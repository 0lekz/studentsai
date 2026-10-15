import os

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://localhost:5432/studentsai_test"
)
os.environ["DEBUG"] = "true"
os.environ["ENVIRONMENT"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "480"
os.environ["VERIFICATION_TOKEN_EXPIRE_MINUTES"] = "1440"
os.environ["FRONTEND_URL"] = "http://localhost:3000"
os.environ["OPENAI_API_KEY"] = "test"
os.environ["SENDGRID_API_KEY"] = "test"
os.environ["EMBEDDING_BACKEND"] = "fake"
os.environ["SIMILARITY_BACKEND"] = "tfidf"
os.environ["LLM_PROVIDER"] = "fake"

import ipaddress
import socket
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import make_url, text
from sqlalchemy.orm import Session

from app import email_service, main
from app.database import Base, engine, get_db
from app.email_service import create_verification_token
from app.schemas import GeneratedFlashcard

PASSWORD = "correct-horse-battery"


@dataclass(frozen=True)
class RegisteredUser:
    id: str
    email: str
    username: str
    password: str
    access_token: str

    @property
    def auth_header(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}


@dataclass
class FakeAI:
    summary: str = "A short stub summary."
    similarities: list[dict] = field(default_factory=list)
    calls: list[tuple[str, dict]] = field(default_factory=list)

    async def summarize_content(self, content: str) -> str:
        self.calls.append(("summarize_content", {"content": content}))
        return self.summary

    async def generate_flashcards_from_content(
        self, content: str, count: int = 5
    ) -> list[GeneratedFlashcard]:
        self.calls.append(
            ("generate_flashcards_from_content", {"content": content, "count": count})
        )
        return [
            GeneratedFlashcard(question=f"Question {n}?", answer=f"Answer {n}")
            for n in range(1, count + 1)
        ]

    def calculate_note_similarities(self, notes: list[dict]) -> list[dict]:
        self.calls.append(("calculate_note_similarities", {"notes": notes}))
        return self.similarities


@dataclass(frozen=True)
class SentEmail:
    kind: str
    to: str
    link: str | None = None


@dataclass
class FakeMailer:
    sent: list[SentEmail] = field(default_factory=list)

    def to(self, address: str) -> list[SentEmail]:
        return [email for email in self.sent if email.to == address]

    async def send_verification_email(
        self, email: str, username: str, verification_url: str
    ) -> None:
        self.sent.append(SentEmail("verification", email, verification_url))

    async def send_password_reset_email(self, email: str, reset_url: str) -> None:
        self.sent.append(SentEmail("password_reset", email, reset_url))

    async def send_account_deletion_email(self, email: str, confirm_url: str) -> None:
        self.sent.append(SentEmail("account_deletion", email, confirm_url))

    async def send_email_change_verification(
        self, new_email: str, verification_url: str
    ) -> None:
        self.sent.append(SentEmail("email_change", new_email, verification_url))

    def send_email_via_sendgrid(
        self, to_email: str, subject: str, html_content: str
    ) -> bool:
        self.sent.append(SentEmail("sendgrid", to_email))
        return True


def _is_local_host(host) -> bool:
    if isinstance(host, bytes):
        host = host.decode()
    if host in (None, "localhost"):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


@pytest.fixture(autouse=True)
def network_guard(monkeypatch) -> Iterator[None]:
    """Fail any test that resolves or connects to a non-loopback host, even if the app swallows the error."""
    attempts: list = []
    real_getaddrinfo = socket.getaddrinfo
    real_connect = socket.socket.connect

    def guarded_getaddrinfo(host, *args, **kwargs):
        if _is_local_host(host):
            return real_getaddrinfo(host, *args, **kwargs)
        attempts.append(host)
        raise socket.gaierror(f"DNS lookups are blocked in tests: {host}")

    def guarded_connect(sock, address):
        is_unix_socket = isinstance(address, str | bytes)
        if is_unix_socket or _is_local_host(address[0]):
            return real_connect(sock, address)
        attempts.append(address)
        raise ConnectionRefusedError(f"Network access is blocked in tests: {address}")

    monkeypatch.setattr(socket, "getaddrinfo", guarded_getaddrinfo)
    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    yield
    assert not attempts, f"Test attempted network access: {attempts}"


@pytest.fixture(autouse=True)
def fake_ai(monkeypatch) -> FakeAI:
    fake = FakeAI()
    monkeypatch.setattr(main, "summarize_content", fake.summarize_content)
    monkeypatch.setattr(
        main, "generate_flashcards_from_content", fake.generate_flashcards_from_content
    )
    monkeypatch.setattr(
        main, "calculate_note_similarities", fake.calculate_note_similarities
    )
    return fake


@pytest.fixture(autouse=True)
def fake_mailer(monkeypatch) -> FakeMailer:
    fake = FakeMailer()
    for name in (
        "send_verification_email",
        "send_password_reset_email",
        "send_account_deletion_email",
        "send_email_change_verification",
    ):
        monkeypatch.setattr(main, name, getattr(fake, name))
    monkeypatch.setattr(
        email_service, "send_email_via_sendgrid", fake.send_email_via_sendgrid
    )
    return fake


@pytest.fixture(scope="session")
def database() -> Iterator[None]:
    expected = make_url(os.environ["DATABASE_URL"])
    if engine.url != expected:
        pytest.exit(
            f"Refusing to run: app engine is bound to {engine.url!r}, expected {expected!r}"
        )
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(database) -> Iterator[Session]:
    """A session whose commits become savepoint releases inside a rolled-back transaction."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        autoflush=False,
        join_transaction_mode="create_savepoint",
    )
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session) -> Iterator[TestClient]:
    main.app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


@pytest.fixture
def register_user(client) -> Callable[..., RegisteredUser]:
    """Register through the API and, unless told otherwise, verify the email through the API."""

    def register(email: str, username: str, *, verified: bool = True):
        response = client.post(
            "/auth/register",
            json={"email": email, "username": username, "password": PASSWORD},
        )
        assert response.status_code == 200, response.text
        if verified:
            verification = client.post(
                "/auth/verify-email", json={"token": create_verification_token(email)}
            )
            assert verification.status_code == 200, verification.text
        body = response.json()
        return RegisteredUser(
            id=body["user"]["id"],
            email=email,
            username=username,
            password=PASSWORD,
            access_token=body["access_token"],
        )

    return register


@pytest.fixture
def user(register_user) -> RegisteredUser:
    return register_user("alice@example.com", "alice")


@pytest.fixture
def other_user(register_user) -> RegisteredUser:
    return register_user("bob@example.com", "bob")


@pytest.fixture
def auth_client(client, user) -> TestClient:
    return TestClient(main.app, headers=user.auth_header)


@pytest.fixture
def other_auth_client(client, other_user) -> TestClient:
    return TestClient(main.app, headers=other_user.auth_header)


@pytest.fixture
def create_course() -> Callable[..., dict]:
    def create(client: TestClient, name: str = "Biology 101", **fields) -> dict:
        response = client.post("/courses", json={"name": name, **fields})
        assert response.status_code == 201, response.text
        return response.json()

    return create


@pytest.fixture
def create_note() -> Callable[..., dict]:
    def create(
        client: TestClient,
        title: str = "Photosynthesis",
        content: str = "Plants convert light energy into chemical energy.",
        course_id: str | None = None,
    ) -> dict:
        payload = {"title": title, "content": content}
        if course_id is not None:
            payload["course_id"] = course_id
        response = client.post("/notes", json=payload)
        assert response.status_code == 200, response.text
        return response.json()

    return create
