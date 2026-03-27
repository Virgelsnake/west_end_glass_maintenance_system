from fastapi import status
from unittest.mock import patch, AsyncMock, MagicMock


def test_get_audit_logs(client, auth_headers):
    """Get audit logs"""
    with patch("app.routers.audit.get_db") as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        # Create a properly mocked cursor that supports chaining
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_db.audit_logs.find.return_value = mock_cursor
        
        response = client.get("/audit", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK


def test_get_audit_logs_by_ticket(client, auth_headers):
    """Get audit logs filtered by ticket"""
    with patch("app.routers.audit.get_db") as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        # Create a properly mocked cursor that supports chaining
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_db.audit_logs.find.return_value = mock_cursor
        
        response = client.get("/audit?ticket_id=123", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK


def test_get_audit_logs_by_machine(client, auth_headers):
    """Get audit logs filtered by machine"""
    with patch("app.routers.audit.get_db") as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        # Create a properly mocked cursor that supports chaining
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_db.audit_logs.find.return_value = mock_cursor
        
        response = client.get("/audit?machine_id=M001", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK


def test_get_audit_logs_by_actor(client, auth_headers):
    """Get audit logs filtered by actor"""
    with patch("app.routers.audit.get_db") as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        # Create a properly mocked cursor that supports chaining
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_db.audit_logs.find.return_value = mock_cursor
        
        response = client.get("/audit?actor=admin", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK


def test_get_audit_logs_by_event(client, auth_headers):
    """Get audit logs filtered by event"""
    with patch("app.routers.audit.get_db") as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        # Create a properly mocked cursor that supports chaining
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_db.audit_logs.find.return_value = mock_cursor
        
        response = client.get("/audit?event=ticket_created", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK


def test_get_audit_logs_paginated(client, auth_headers):
    """Get audit logs with pagination"""
    with patch("app.routers.audit.get_db") as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        # Create a properly mocked cursor that supports chaining
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_db.audit_logs.find.return_value = mock_cursor
        
        response = client.get("/audit?skip=10&limit=50", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
