from fastapi import status
from unittest.mock import patch, AsyncMock, MagicMock
from bson import ObjectId


def test_list_machines(client, auth_headers, test_machine_doc):
    """List all machines returns array"""
    with patch("app.routers.machines.get_db") as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        # Create a properly mocked cursor that supports chaining
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=[test_machine_doc])
        mock_db.machines.find.return_value = mock_cursor
        
        response = client.get("/machines", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) > 0


def test_create_machine(client, auth_headers):
    """Create new machine"""
    with patch("app.routers.machines.get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        mock_db.machines.find_one.return_value = None
        mock_db.machines.insert_one.return_value.inserted_id = ObjectId()
        
        payload = {"machine_id": "M001", "name": "Test", "location": "A"}
        response = client.post("/machines", json=payload, headers=auth_headers)
        assert response.status_code == status.HTTP_201_CREATED


def test_create_duplicate_machine(client, auth_headers, test_machine_doc):
    """Duplicate machine ID returns 409"""
    with patch("app.routers.machines.get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        mock_db.machines.find_one.return_value = test_machine_doc
        
        payload = {"machine_id": "MACH-001", "name": "Dup", "location": "B"}
        response = client.post("/machines", json=payload, headers=auth_headers)
        assert response.status_code == status.HTTP_409_CONFLICT


def test_get_machine(client, auth_headers, test_machine_doc):
    """Get specific machine"""
    with patch("app.routers.machines.get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        mock_db.machines.find_one.return_value = test_machine_doc
        
        response = client.get("/machines/MACH-001", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK


def test_get_machine_not_found(client, auth_headers):
    """Get nonexistent machine returns 404"""
    with patch("app.routers.machines.get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        mock_db.machines.find_one.return_value = None
        
        response = client.get("/machines/INVALID", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_machine(client, auth_headers):
    """Update machine"""
    with patch("app.routers.machines.get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        mock_db.machines.update_one.return_value.matched_count = 1
        
        response = client.patch(
            "/machines/MACH-001",
            json={"location": "B"},
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK


def test_update_machine_not_found(client, auth_headers):
    """Update nonexistent machine returns 404"""
    with patch("app.routers.machines.get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        mock_db.machines.update_one.return_value.matched_count = 0
        
        response = client.patch(
            "/machines/INVALID",
            json={"location": "B"},
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
