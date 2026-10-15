import uuid
from datetime import datetime, timedelta

import pytest
from jose import jwt

from app.auth import create_access_token
from app.config import settings
from app.email_service import (
    create_email_change_token,
    create_password_reset_token,
    create_verification_token,
)

ME = "/api/settings/profile"
CHANGE_LINK_PREFIX = "http://localhost:3000/verify-email-change/"
NEW_EMAIL = "alice.new@example.com"


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


def test_register_returns_a_token_for_an_unverified_user(client):
    response = register(client)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert token_subject(body["access_token"]) == "carol@example.com"
    assert body["user"]["email"] == "carol@example.com"
    assert body["user"]["username"] == "carol"
    assert body["user"]["verified"] is False
    assert body["user"]["has_password"] is True
    assert "plan" not in body["user"]


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


def test_malformed_verification_token_returns_400(client):
    assert client.post("/auth/verify-email", json={"token": "x"}).status_code == 400
    assert client.get("/auth/verify/not-a-jwt").status_code == 400


def test_malformed_password_reset_token_returns_400(client):
    response = client.post(
        "/auth/reset-password", json={"token": "x", "new_password": "brand-new-pass"}
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid or expired token"}


def request_email_change(client, user, new_email=NEW_EMAIL):
    return client.post(
        "/auth/send-email-change-verification",
        headers=user.auth_header,
        json={"new_email": new_email},
    )


def change_token(fake_mailer, address: str) -> str:
    [email] = [sent for sent in fake_mailer.to(address) if sent.kind == "email_change"]
    assert email.link.startswith(CHANGE_LINK_PREFIX)
    return email.link.removeprefix(CHANGE_LINK_PREFIX)


def confirm_email_change(client, token: str):
    return client.post("/auth/verify-email-change", json={"token": token})


def test_email_change_emails_a_link_to_the_new_address_only(client, user, fake_mailer):
    response = request_email_change(client, user)

    assert response.status_code == 200
    assert response.json() == {
        "message": "Verification email sent to your new email address",
        "data": None,
    }
    change_token(fake_mailer, NEW_EMAIL)
    assert [sent.kind for sent in fake_mailer.to(user.email)] == ["verification"]
    assert client.get(ME, headers=user.auth_header).json()["email"] == user.email


def test_confirming_an_email_change_switches_the_address(client, user, fake_mailer):
    request_email_change(client, user)

    response = confirm_email_change(client, change_token(fake_mailer, NEW_EMAIL))

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Email address updated successfully"
    assert body["verified"] is True
    assert token_subject(body["access_token"]) == NEW_EMAIL
    me = client.get(ME, headers=bearer(body["access_token"])).json()
    assert (me["id"], me["email"], me["verified"]) == (user.id, NEW_EMAIL, True)
    assert client.get(ME, headers=user.auth_header).status_code == 401
    login = client.post(
        "/auth/login", json={"email": NEW_EMAIL, "password": user.password}
    )
    assert login.status_code == 200


def test_confirming_the_same_email_change_twice_is_harmless(client, user, fake_mailer):
    request_email_change(client, user)
    token = change_token(fake_mailer, NEW_EMAIL)
    confirm_email_change(client, token)

    response = confirm_email_change(client, token)

    assert response.status_code == 200
    assert response.json() == {
        "message": "Email address already updated",
        "verified": True,
        "access_token": None,
    }


def test_an_email_change_link_is_stale_once_another_change_went_through(
    client, user, fake_mailer
):
    request_email_change(client, user, "first@example.com")
    request_email_change(client, user, "second@example.com")
    first = change_token(fake_mailer, "first@example.com")
    second = change_token(fake_mailer, "second@example.com")

    assert confirm_email_change(client, second).status_code == 200
    response = confirm_email_change(client, first)

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid or expired verification token"}


def test_email_change_to_an_address_in_use_returns_400(
    client, user, other_user, fake_mailer
):
    response = request_email_change(client, user, other_user.email)

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Email address is already in use by another account"
    }
    assert [sent.kind for sent in fake_mailer.to(other_user.email)] == ["verification"]


def test_email_change_to_the_current_address_returns_400(client, user):
    response = request_email_change(client, user, user.email)

    assert response.status_code == 400
    assert response.json() == {"detail": "This is already your email address"}


def test_email_change_to_an_invalid_address_returns_422(client, user):
    assert request_email_change(client, user, "not-an-email").status_code == 422


def test_confirming_an_email_change_after_the_address_was_taken_returns_400(
    client, user, register_user, fake_mailer
):
    request_email_change(client, user)
    token = change_token(fake_mailer, NEW_EMAIL)
    register_user(NEW_EMAIL, "carol")

    response = confirm_email_change(client, token)

    assert response.status_code == 400
    assert client.get(ME, headers=user.auth_header).json()["email"] == user.email


@pytest.mark.parametrize(
    "token",
    ["not-a-jwt", create_verification_token(NEW_EMAIL)],
    ids=["malformed", "other-token-type"],
)
def test_confirming_an_email_change_with_an_invalid_token_returns_400(client, token):
    response = confirm_email_change(client, token)

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid or expired verification token"}


def test_confirming_an_email_change_for_a_deleted_user_returns_404(client):
    token = create_email_change_token(uuid.uuid4(), "gone@example.com", NEW_EMAIL)

    assert confirm_email_change(client, token).status_code == 404


def test_profile_update_cannot_change_the_email_without_verification(client, user):
    response = client.patch(
        ME, headers=user.auth_header, json={"email": NEW_EMAIL, "username": "alicia"}
    )

    assert response.status_code == 200
    assert (response.json()["email"], response.json()["username"]) == (
        user.email,
        "alicia",
    )
