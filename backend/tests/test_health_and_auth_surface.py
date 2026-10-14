import re

import pytest
from fastapi.routing import APIRoute

from app.main import app

PUBLIC_ROUTES = {
    ("GET", "/health"),
    ("POST", "/auth/register"),
    ("POST", "/auth/login"),
    ("GET", "/auth/google/login"),
    ("GET", "/auth/google/callback"),
    ("POST", "/auth/google"),
    ("POST", "/auth/send-verification"),
    ("GET", "/auth/verify/{token}"),
    ("POST", "/auth/verify-email"),
    ("GET", "/auth/verify-email-change-step1/{token}"),
    ("GET", "/auth/verify-email-change-step2/{token}"),
    ("POST", "/auth/forgot-password"),
    ("POST", "/auth/reset-password"),
    ("POST", "/auth/confirm-account-deletion"),
}

ALL_ROUTES = sorted(
    (method, route.path)
    for route in app.routes
    if isinstance(route, APIRoute)
    for method in route.methods
)
PROTECTED_ROUTES = [route for route in ALL_ROUTES if route not in PUBLIC_ROUTES]


def concrete_path(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "00000000-0000-0000-0000-000000000000", path)


def route_id(route: tuple[str, str]) -> str:
    return " ".join(route)


def test_health_returns_healthy(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "StudentsAI MVP API"}


def test_every_known_public_route_exists():
    assert PUBLIC_ROUTES.issubset(ALL_ROUTES)


@pytest.mark.parametrize("route", PROTECTED_ROUTES, ids=route_id)
def test_protected_route_without_token_is_rejected(client, route):
    method, path = route

    response = client.request(method, concrete_path(path))

    assert response.status_code in {401, 403}


@pytest.mark.parametrize("route", PROTECTED_ROUTES, ids=route_id)
def test_protected_route_with_invalid_token_returns_401(client, route):
    method, path = route

    response = client.request(
        method, concrete_path(path), headers={"Authorization": "Bearer not-a-jwt"}
    )

    assert response.status_code == 401
