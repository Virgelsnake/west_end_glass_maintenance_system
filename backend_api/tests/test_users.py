from fastapi import status
from unittest.mock import patch, AsyncMock, MagicMock
from bson import ObjectId


def test_list_users(client, auth_headers, test_user_doc):
    """List all users returns array"""
    with patch("app.routers.users.get_db") as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        # Create a properly mocked cursor that supports chaining
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=[test_user_doc])
        mock_db.users.find.return_value = mock_cursor
        
        response = client.get("/users", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK


def test_create_user(client, auth_headers):
    """Create new user"""
    with patch("app.routers.users.get_db") as mock_get_db:
        with patch("app.routers.users.log_event"):
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            mock_db.users.find_one.return_value = None
            mock_db.users.insert_one.return_value.inserted_id = ObjectId()
            
            payload = {"name": "John", "phone_number": "+1111111111", "active": True}
            response = client.post("/users", json=payload, headers=auth_headers)
            assert response.status_code == status.HTTP_201_CREATED


def test_create_duplicate_user(client, auth_headers, test_user_doc):
    """Duplicate user returns 409"""
    with patch("app.routers.users.get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        mock_db.users.find_one.return_value = test_user_doc
        
        payload = {"name": "Dup", "phone_number": "+1234567890", "active": True}
        response = client.post("/users", json=payload, headers=auth_headers)
        assert response.status_code == status.HTTP_409_CONFLICT


def test_update_user(client, auth_headers):
    """Update user"""
    with patch("app.routers.users.get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        mock_db.users.update_one.return_value.matched_count = 1
        
        response = client.patch(
            "/users/+1234567890",
            json={"name": "Updated"},
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK


def test_update_user_not_found(client, auth_headers):
    """Update nonexistent user returns 404"""
    with patch("app.routers.users.get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        mock_db.users.update_one.return_value.matched_count = 0
        
        response = client.patch(
            "/users/+0000000000",
            json={"name": "X"},
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


def test_deactivate_user(client, auth_headers):
    """Deactivate user"""
    with patch("app.routers.users.get_db") as mock_get_db:
        with patch("app.routers.users.log_event"):
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            mock_db.users.update_one.return_value.matched_count = 1
            
            response = client.delete("/users/+1234567890", headers=auth_headers)
            assert response.status_code == status.HTTP_200_OK


def test_deactivate_user_not_found(client, auth_headers):
    """Deactivate nonexistent user returns 404"""
    with patch("app.routers.users.get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        mock_db.users.update_one.return_value.matched_count = 0
        
        response = client.delete("/users/+0000000000", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND
