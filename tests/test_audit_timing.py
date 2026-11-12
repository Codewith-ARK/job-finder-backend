from unittest.mock import patch

from app.services import auth_service


def test_unknown_login_still_verifies_password(client):
    with patch.object(auth_service, "verify_password", return_value=False) as verify:
        response = client.post("/api/auth/login", json={
            "email": "absent@example.com", "password": "incorrect",
        })
        assert response.status_code == 401
        verify.assert_called_once()
