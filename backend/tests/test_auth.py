from datetime import datetime, timedelta

from jose import jwt

from app.auth import create_access_token
from app.config import settings
from app.email_service import create_password_reset_token, create_verification_token

ME = "/api/settings/profile"


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def token_subject(token: str) -> str:
    claims = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    return claims["sub"]


def register(
    client, email="carol@example.com", username="carol", password="s3cret-pass"
):
    return client.post(
        "/auth/register",
        json={"email": email, "username": username, "password": password},
    )


def test_register_returns_a_token_for_an_unverified_free_user(client):
    response = register(client)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert token_subject(body["access_token"]) == "carol@example.com"
    assert body["user"]["email"] == "carol@example.com"
    assert body["user"]["username"] == "carol"
    assert body["user"]["verified"] is False
    assert body["user"]["has_password"] is True
    assert body["user"]["plan"] == "free"


def test_register_emails_a_verification_link_that_verifies_the_account(
    client, fake_mailer
):
    register(client)

    [email] = fake_mailer.to("carol@example.com")
    assert email.kind == "verification"
    assert email.link.startswith("http://localhost:3000/verify/")
    token = email.link.removeprefix("http://localhost:3000/verify/")

    response = client.get(f"/auth/verify/{token}")

    assert response.status_code == 200
    assert response.json()["message"] == "Email verified successfully"
    login = client.post(
        "/auth/login", json={"email": "carol@example.com", "password": "s3cret-pass"}
    )
    assert login.status_code == 200


def test_register_without_username_generates_one(client):
    response = client.post(
        "/auth/register", json={"email": "carol@example.com", "password": "s3cret-pass"}
    )

    assert response.status_code == 200
    assert response.json()["user"]["username"].startswith("user_")


def test_register_with_taken_email_returns_400(client, user):
    response = register(client, email=user.email, username="someone-else")

    assert response.status_code == 400
    assert response.json() == {"detail": "Email already registered"}


def test_register_with_taken_username_returns_400(client, user):
    response = register(client, email="new@example.com", username=user.username)

    assert response.status_code == 400
    assert response.json() == {"detail": "Username already taken"}


def test_register_without_password_returns_400(client):
    response = client.post("/auth/register", json={"email": "carol@example.com"})

    assert response.status_code == 400
    assert response.json() == {"detail": "Password is required for registration"}


def test_register_with_short_password_returns_422(client):
    assert register(client, password="short").status_code == 422


def test_verify_email_marks_user_verified_and_is_idempotent(client, register_user):
    unverified = register_user("carol@example.com", "carol", verified=False)
    token = create_verification_token(unverified.email)

    first = client.post("/auth/verify-email", json={"token": token})
    second = client.post("/auth/verify-email", json={"token": token})

    assert first.json() == {
        "message": "Email verified successfully",
        "verified": True,
        "access_token": None,
    }
    assert second.json()["message"] == "Email already verified"
    me = client.get(ME, headers=unverified.auth_header).json()
    assert me["verified"] is True


def test_login_with_correct_password_returns_a_token(client, user):
    response = client.post(
        "/auth/login", json={"email": user.email, "password": user.password}
    )

    assert response.status_code == 200
    body = response.json()
    assert token_subject(body["access_token"]) == user.email
    assert body["user"]["id"] == user.id
    assert body["user"]["verified"] is True


def test_login_with_wrong_password_returns_401(client, user):
    response = client.post(
        "/auth/login", json={"email": user.email, "password": "not-the-password"}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect email or password"}


def test_login_with_unknown_email_returns_401(client):
    response = client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": "whatever-pass"}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect email or password"}


def test_login_before_email_verification_returns_403(client, register_user):
    unverified = register_user("carol@example.com", "carol", verified=False)

    response = client.post(
        "/auth/login",
        json={"email": unverified.email, "password": unverified.password},
    )

    assert response.status_code == 403
    assert response.json()["detail"].startswith("Please verify your email address")


def test_refresh_with_valid_token_returns_a_working_token(client, user):
    response = client.post("/auth/refresh", headers=user.auth_header)

    assert response.status_code == 200
    refreshed = response.json()["access_token"]
    assert token_subject(refreshed) == user.email
    assert client.get(ME, headers=bearer(refreshed)).status_code == 200


def test_refresh_without_token_returns_403(client):
    response = client.post("/auth/refresh")

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authenticated"}


def test_refresh_with_invalid_token_returns_401(client):
    response = client.post("/auth/refresh", headers=bearer("not-a-jwt"))

    assert response.status_code == 401


def test_protected_route_with_valid_token_returns_current_user(client, user):
    response = client.get(ME, headers=user.auth_header)

    assert response.status_code == 200
    assert response.json()["id"] == user.id
    assert response.json()["email"] == user.email


def test_protected_route_without_token_returns_403(client):
    # FastAPI 0.104's HTTPBearer answers a missing header with 403, not 401.
    response = client.get(ME)

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authenticated"}


def test_protected_route_with_malformed_token_returns_401(client):
    response = client.get(ME, headers=bearer("not-a-jwt"))

    assert response.status_code == 401
    assert response.json() == {"detail": "Could not validate credentials"}
    assert response.headers["www-authenticate"] == "Bearer"


def test_protected_route_with_token_signed_by_another_key_returns_401(client, user):
    forged = jwt.encode(
        {"sub": user.email, "exp": datetime.utcnow() + timedelta(minutes=5)},
        "some-other-key",
        algorithm="HS256",
    )

    assert client.get(ME, headers=bearer(forged)).status_code == 401


def test_protected_route_with_expired_token_returns_401(client, user):
    expired = create_access_token(
        {"sub": user.email}, expires_delta=timedelta(minutes=-1)
    )

    assert client.get(ME, headers=bearer(expired)).status_code == 401


def test_protected_route_with_token_without_subject_returns_401(client):
    assert client.get(ME, headers=bearer(create_access_token({}))).status_code == 401


def test_protected_route_with_token_for_unknown_user_returns_401(client):
    ghost = create_access_token({"sub": "ghost@example.com"})

    assert client.get(ME, headers=bearer(ghost)).status_code == 401


def test_unverified_user_can_use_routes_that_only_require_a_token(
    client, register_user
):
    unverified = register_user("carol@example.com", "carol", verified=False)

    assert client.get("/notes", headers=unverified.auth_header).status_code == 200


def test_unverified_user_is_rejected_by_routes_that_require_verification(
    client, register_user
):
    unverified = register_user("carol@example.com", "carol", verified=False)

    response = client.post(
        "/flashcards/generate",
        headers=unverified.auth_header,
        json={"mode": "single", "note_id": "00000000-0000-0000-0000-000000000000"},
    )

    assert response.status_code == 403
    assert response.json()["detail"].startswith("Email verification required")


def test_forgot_password_emails_a_reset_link_to_a_known_user(client, user, fake_mailer):
    response = client.post("/auth/forgot-password", json={"email": user.email})

    assert response.json() == {
        "message": "If that email exists, a reset link has been sent."
    }
    [email] = [
        sent for sent in fake_mailer.to(user.email) if sent.kind != "verification"
    ]
    assert email.kind == "password_reset"
    assert email.link.endswith("?type=password_reset")


def test_forgot_password_for_unknown_email_gives_the_same_answer_and_sends_nothing(
    client, fake_mailer
):
    response = client.post(
        "/auth/forgot-password", json={"email": "nobody@example.com"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "If that email exists, a reset link has been sent."
    }
    assert fake_mailer.sent == []


def test_reset_password_replaces_the_password_used_for_login(client, user):
    token = create_password_reset_token(user.email)

    response = client.post(
        "/auth/reset-password", json={"token": token, "new_password": "brand-new-pass"}
    )

    assert response.status_code == 200
    old_login = client.post(
        "/auth/login", json={"email": user.email, "password": user.password}
    )
    new_login = client.post(
        "/auth/login", json={"email": user.email, "password": "brand-new-pass"}
    )
    assert old_login.status_code == 401
    assert new_login.status_code == 200
