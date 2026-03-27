from fastapi import status
from unittest.mock import patch, AsyncMock, MagicMock
from bson import ObjectId


def test_list_tickets(client, auth_headers, test_ticket_doc):
    """List all tickets returns array"""
    with patch("app.routers.tickets.get_db") as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        # Create a properly mocked cursor that supports chaining
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=[test_ticket_doc])
        mock_db.tickets.find.return_value = mock_cursor
        
        response = client.get("/tickets", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK


def test_list_tickets_filtered(client, auth_headers, test_ticket_doc):
    """List tickets with filters"""
    with patch("app.routers.tickets.get_db") as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        # Create a properly mocked cursor that supports chaining
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=[test_ticket_doc])
        mock_db.tickets.find.return_value = mock_cursor
        
        response = client.get("/tickets?status=open", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK


def test_create_ticket(client, auth_headers):
    """Create new ticket"""
    with patch("app.routers.tickets.get_db") as mock_get_db:
        with patch("app.routers.tickets.log_event"):
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            mock_db.tickets.insert_one.return_value.inserted_id = ObjectId()
            
            payload = {"machine_id": "M001", "title": "Test", "description": "Issue"}
            response = client.post("/tickets", json=payload, headers=auth_headers)
            assert response.status_code == status.HTTP_201_CREATED


def test_get_ticket(client, auth_headers, test_ticket_doc):
    """Get specific ticket"""
    ticket_id = str(test_ticket_doc["_id"])
    with patch("app.routers.tickets.get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        mock_db.tickets.find_one.return_value = test_ticket_doc
        
        response = client.get(f"/tickets/{ticket_id}", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK


def test_get_ticket_invalid_id(client, auth_headers):
    """Invalid ticket ID returns 400"""
    # No need to mock get_db for ID validation test - the ID validation happens before any DB call
    with patch("app.routers.tickets.get_db") as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        response = client.get("/tickets/invalid", headers=auth_headers)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_get_ticket_not_found(client, auth_headers):
    """Nonexistent ticket returns 404"""
    ticket_id = str(ObjectId())
    with patch("app.routers.tickets.get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        mock_db.tickets.find_one.return_value = None
        
        response = client.get(f"/tickets/{ticket_id}", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_ticket(client, auth_headers, test_ticket_doc):
    """Update ticket"""
    ticket_id = str(test_ticket_doc["_id"])
    with patch("app.routers.tickets.get_db") as mock_get_db:
        with patch("app.routers.tickets.log_event"):
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            mock_db.tickets.update_one.return_value.matched_count = 1
            mock_db.tickets.find_one.return_value = test_ticket_doc
            
            response = client.patch(
                f"/tickets/{ticket_id}",
                json={"status": "in_progress"},
                headers=auth_headers
            )
            assert response.status_code == status.HTTP_200_OK


def test_update_ticket_empty(client, auth_headers, test_ticket_doc):
    """Update ticket with no fields returns 400"""
    ticket_id = str(test_ticket_doc["_id"])
    with patch("app.routers.tickets.get_db") as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        response = client.patch(f"/tickets/{ticket_id}", json={}, headers=auth_headers)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_close_ticket(client, auth_headers, test_ticket_doc):
    """Close ticket"""
    ticket_id = str(test_ticket_doc["_id"])
    with patch("app.routers.tickets.get_db") as mock_get_db:
        with patch("app.routers.tickets.log_event"):
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            mock_db.tickets.update_one.return_value = AsyncMock()
            mock_db.tickets.find_one.return_value = test_ticket_doc
            
            response = client.post(f"/tickets/{ticket_id}/close", headers=auth_headers)
            assert response.status_code == status.HTTP_200_OK


# ─── Reference photos tests ───────────────────────────────────────────────────

def test_add_reference_photo_success(client, auth_headers, test_ticket_doc):
    """Successfully attaching a reference photo returns filenames and whatsapp_sent field."""
    ticket_id = str(test_ticket_doc["_id"])
    with patch("app.routers.tickets.get_db") as mock_get_db, \
         patch("app.routers.tickets.log_event"), \
         patch("app.routers.tickets.os.makedirs"), \
         patch("app.routers.tickets.shutil.copyfileobj"), \
         patch("builtins.open", new_callable=MagicMock):

        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        # No assigned_to — WhatsApp branch is skipped entirely
        mock_db.tickets.find_one.return_value = {
            **test_ticket_doc,
            "assigned_to": None,
            "reference_photos": [],
        }
        mock_db.tickets.update_one.return_value = AsyncMock()

        img_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 20  # minimal JPEG-ish bytes
        response = client.post(
            f"/tickets/{ticket_id}/reference_photos",
            headers=auth_headers,
            files=[("photos", ("test.jpg", img_bytes, "image/jpeg"))],
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "filenames" in data
    assert len(data["filenames"]) == 1
    assert "whatsapp_sent" in data


def test_add_reference_photo_invalid_ticket(client, auth_headers):
    """Returns 404 when ticket does not exist."""
    ticket_id = str(ObjectId())
    with patch("app.routers.tickets.get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        mock_db.tickets.find_one.return_value = None

        img_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 20
        response = client.post(
            f"/tickets/{ticket_id}/reference_photos",
            headers=auth_headers,
            files=[("photos", ("test.jpg", img_bytes, "image/jpeg"))],
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_add_reference_photo_whatsapp_failure_nonfatal(client, auth_headers, test_ticket_doc):
    """WhatsApp send failure is non-fatal — ticket still returns 200."""
    ticket_id = str(test_ticket_doc["_id"])
    with patch("app.routers.tickets.get_db") as mock_get_db, \
         patch("app.routers.tickets.log_event"), \
         patch("app.routers.tickets.os.makedirs"), \
         patch("app.routers.tickets.shutil.copyfileobj"), \
         patch("builtins.open", new_callable=MagicMock), \
         patch("app.services.whatsapp.send_ticket_photo", new_callable=AsyncMock,
               side_effect=Exception("network error")):

        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        mock_db.tickets.find_one.return_value = {
            **test_ticket_doc,
            "reference_photos": [],
            "assigned_to": "+1234567890",
        }
        mock_db.tickets.update_one.return_value = AsyncMock()

        img_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 20
        response = client.post(
            f"/tickets/{ticket_id}/reference_photos",
            headers=auth_headers,
            files=[("photos", ("test.jpg", img_bytes, "image/jpeg"))],
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["whatsapp_sent"] is False
