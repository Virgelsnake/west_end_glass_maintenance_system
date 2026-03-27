from fastapi import status
from unittest.mock import patch, AsyncMock


def test_login_success(client, test_admin_doc):
    """Admin login returns JWT token"""
    with patch("app.routers.admin_auth.get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        mock_db.admins.find_one.return_value = test_admin_doc
        
        response = client.post(
            "/auth/login",
            data={"username": "admin", "password": "Monday001!"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.json()


def test_login_invalid_password(client, test_admin_doc):
    """Invalid password returns 401"""
    with patch("app.routers.admin_auth.get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        mock_db.admins.find_one.return_value = test_admin_doc
        
        response = client.post(
            "/auth/login",
            data={"username": "admin", "password": "wrong"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_login_user_not_found(client):
    """Unknown user returns 401"""
    with patch("app.routers.admin_auth.get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        mock_db.admins.find_one.return_value = None
        
        response = client.post(
            "/auth/login",
            data={"username": "invalid", "password": "password"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_me(client, auth_headers):
    """Get current admin with valid token"""
    response = client.get("/auth/me", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    assert "username" in response.json()


def test_get_me_no_token(client):
    """Accessing protected route without token returns 401"""
    response = client.get("/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
