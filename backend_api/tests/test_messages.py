from fastapi import status
from unittest.mock import patch, AsyncMock, MagicMock
from bson import ObjectId


def test_get_messages(client, auth_headers, test_ticket_doc):
    """Get messages for ticket"""
    ticket_id = str(test_ticket_doc["_id"])
    with patch("app.routers.messages.get_db") as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        # Create a properly mocked cursor that supports chaining
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_db.messages.find.return_value = mock_cursor
        
        response = client.get(f"/tickets/{ticket_id}/messages", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK


def test_send_message(client, auth_headers, test_ticket_doc):
    """Admin sends message to ticket"""
    ticket_id = str(test_ticket_doc["_id"])
    with patch("app.routers.messages.get_db") as mock_get_db:
        with patch("app.services.whatsapp.send_text_message"):
            with patch("app.services.audit_service.log_event"):
                mock_db = MagicMock()
                mock_get_db.return_value = mock_db
                mock_db.tickets.find_one = AsyncMock(return_value=test_ticket_doc)
                mock_db.messages.insert_one = AsyncMock()
                
                payload = {"text": "Test message"}
                response = client.post(
                    f"/tickets/{ticket_id}/messages",
                    json=payload,
                    headers=auth_headers
                )
                assert response.status_code == status.HTTP_200_OK


def test_send_message_ticket_not_found(client, auth_headers):
    """Send message to nonexistent ticket returns 404"""
    ticket_id = str(ObjectId())
    with patch("app.routers.messages.get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        mock_db.tickets.find_one.return_value = None
        
        response = client.post(
            f"/tickets/{ticket_id}/messages",
            json={"text": "Test"},
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


def test_send_message_empty_text(client, auth_headers, test_ticket_doc):
    """Send message with empty text returns 400"""
    ticket_id = str(test_ticket_doc["_id"])
    with patch("app.routers.messages.get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        mock_db.tickets.find_one.return_value = test_ticket_doc
        
        response = client.post(
            f"/tickets/{ticket_id}/messages",
            json={"text": ""},
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
