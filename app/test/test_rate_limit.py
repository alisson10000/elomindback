import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.rate_limit import limiter, rate_limit_exceeded_handler
from app.db.session import get_db
from app.modules.auth import router as auth_router_module
from app.modules.auth.password_reset import router as password_reset_router_module
from app.modules.invitations import router as invitations_router_module


def override_get_db():
    yield SimpleNamespace()


class RateLimitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app = FastAPI()
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
        app.add_middleware(SlowAPIMiddleware)
        app.include_router(auth_router_module.router, prefix="/auth", tags=["Auth"])
        app.include_router(password_reset_router_module.router, prefix="/auth", tags=["Auth"])
        app.include_router(invitations_router_module.router)
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[invitations_router_module.require_therapist] = (
            lambda: SimpleNamespace(id=99, role="therapist")
        )
        cls.client = TestClient(app)

    def setUp(self):
        limiter.reset()

    def assert_rate_limit(self, method: str, url: str, payload: dict, limit: int, ip: str):
        headers = {"X-Forwarded-For": ip}

        for _ in range(limit):
            response = self.client.request(method, url, json=payload, headers=headers)
            self.assertNotEqual(response.status_code, 429)

        blocked_response = self.client.request(method, url, json=payload, headers=headers)
        self.assertEqual(blocked_response.status_code, 429)
        self.assertEqual(blocked_response.json(), {"detail": "Too many requests"})

    @patch("app.modules.auth.router.signup", return_value="signup-token")
    def test_signup_rate_limit(self, _mock_signup):
        self.assert_rate_limit(
            "POST",
            "/auth/signup",
            {
                "email": "signup@example.com",
                "name": "Signup User",
                "password": "12345678",
                "role": "client",
            },
            3,
            "10.0.0.1",
        )

    @patch("app.modules.auth.router.login", return_value="login-token")
    def test_login_rate_limit(self, _mock_login):
        self.assert_rate_limit(
            "POST",
            "/auth/login",
            {
                "email": "login@example.com",
                "password": "12345678",
            },
            5,
            "10.0.0.2",
        )

    @patch("app.modules.auth.password_reset.router.log_action", return_value=None)
    @patch("app.modules.auth.password_reset.router.send_email", return_value=None)
    @patch("app.modules.auth.password_reset.router.create_password_reset", return_value=None)
    def test_forgot_password_rate_limit(
        self,
        _mock_create_password_reset,
        _mock_send_email,
        _mock_log_action,
    ):
        self.assert_rate_limit(
            "POST",
            "/auth/forgot-password",
            {"email": "forgot@example.com"},
            3,
            "10.0.0.3",
        )

    @patch("app.modules.auth.password_reset.router.log_action", return_value=None)
    @patch("app.modules.auth.password_reset.router.reset_password_with_token", return_value=True)
    def test_reset_password_rate_limit(self, _mock_reset_password, _mock_log_action):
        self.assert_rate_limit(
            "POST",
            "/auth/reset-password",
            {
                "email": "reset@example.com",
                "token": "reset-token-123",
                "password": "12345678",
            },
            3,
            "10.0.0.4",
        )

    @patch("app.modules.invitations.router.send_email", return_value=None)
    @patch(
        "app.modules.invitations.router.create_invitation",
        return_value=(SimpleNamespace(email="invite@example.com"), "invite-token-123"),
    )
    def test_create_invitation_rate_limit(self, _mock_create_invitation, _mock_send_email):
        self.assert_rate_limit(
            "POST",
            "/invitations",
            {"email": "invite@example.com"},
            10,
            "10.0.0.5",
        )

    @patch(
        "app.modules.invitations.router.serialize_user",
        return_value={
            "id": 1,
            "email": "client@example.com",
            "name": "Client User",
            "role": "client",
            "is_active": True,
        },
    )
    @patch(
        "app.modules.invitations.router.signup_from_invitation",
        return_value=SimpleNamespace(id=1),
    )
    def test_invitation_signup_rate_limit(self, _mock_signup, _mock_serialize_user):
        self.assert_rate_limit(
            "POST",
            "/invitations/signup",
            {
                "token": "invite-token-123",
                "name": "Client User",
                "password": "12345678",
            },
            5,
            "10.0.0.6",
        )


if __name__ == "__main__":
    unittest.main()
