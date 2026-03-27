"""Tests for the WhatsApp simulator endpoint - both modes"""
from fastapi import status
from unittest.mock import patch, AsyncMock, MagicMock
from bson import ObjectId
from datetime import datetime


def test_simulator_auth_failure(client):
    """Test simulator rejects unauthorized users"""
    with patch("app.routers.simulate.get_db") as mock_get_db, \
         patch("app.routers.simulate.process_inbound_message") as mock_process:
        
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_process.return_value = {
            "authorized": False,
            "response_text": "Sorry, this number is not registered."
        }
        
        response = client.post(
            "/simulate/message",
            json={"phone_number": "+15559999999", "message_text": "test"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert not response.json()["authorized"]


def test_simulator_mode_1_chat(client, test_user_doc, test_ticket_doc):
    """Mode 1: Chat-based - send message, auto-find tickets"""
    phone = "+15551234567"
    
    with patch("app.routers.simulate.get_db") as mock_get_db, \
         patch("app.routers.simulate.process_inbound_message") as mock_process:
        
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_process.return_value = {
            "authorized": True,
            "response_text": "I found an open ticket for you.",
            "ticket_id": str(test_ticket_doc["_id"]),
            "ticket_title": test_ticket_doc.get("title"),
            "ticket_status": test_ticket_doc.get("status"),
            "machine_id": test_ticket_doc.get("machine_id"),
            "assigned_to": phone,
        }
        
        response = client.post(
            "/simulate/message",
            json={"phone_number": phone, "message_text": "What tickets do I have?"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["authorized"] is True
        assert data["ticket_id"] is not None
        assert "found" in data["response_text"].lower()


def test_simulator_mode_2_deeplink(client, test_user_doc, test_ticket_doc):
    """Mode 2: Deep-link - start with machine ID"""
    phone = "+15551234567"
    machine_id = "WEG-MACHINE-001"
    
    with patch("app.routers.simulate.get_db") as mock_get_db, \
         patch("app.routers.simulate.process_inbound_message") as mock_process:
        
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_process.return_value = {
            "authorized": True,
            "response_text": f"Starting ticket for {machine_id}.",
            "ticket_id": str(test_ticket_doc["_id"]),
            "ticket_title": test_ticket_doc.get("title"),
            "ticket_status": test_ticket_doc.get("status"),
            "machine_id": machine_id,
            "assigned_to": phone,
        }
        
        response = client.post(
            "/simulate/message",
            json={"phone_number": phone, "message_text": machine_id}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["authorized"] is True
        assert data["machine_id"] == machine_id
        assert data["ticket_id"] is not None


def test_simulator_mode_1_no_tickets(client, test_user_doc):
    """Mode 1: When user has no assigned tickets"""
    phone = "+15551234567"
    
    with patch("app.routers.simulate.get_db") as mock_get_db, \
         patch("app.routers.simulate.process_inbound_message") as mock_process:
        
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_process.return_value = {
            "authorized": True,
            "response_text": "No open tickets assigned to you.",
            "ticket_id": None,
            "ticket_title": None,
            "ticket_status": None,
            "machine_id": None,
            "assigned_to": phone,
        }
        
        response = client.post(
            "/simulate/message",
            json={"phone_number": phone, "message_text": "Hi"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["authorized"] is True
        assert data["ticket_id"] is None
        assert "no" in data["response_text"].lower()


def test_simulator_mode_2_machine_not_found(client, test_user_doc):
    """Mode 2: When machine ID doesn't exist or has no tickets"""
    phone = "+15551234567"
    invalid_machine = "WEG-MACHINE-INVALID"
    
    with patch("app.routers.simulate.get_db") as mock_get_db, \
         patch("app.routers.simulate.process_inbound_message") as mock_process:
        
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_process.return_value = {
            "authorized": True,
            "response_text": f"No open ticket found for {invalid_machine}.",
            "ticket_id": None,
            "ticket_title": None,
            "ticket_status": None,
            "machine_id": invalid_machine,
            "assigned_to": phone,
        }
        
        response = client.post(
            "/simulate/message",
            json={"phone_number": phone, "message_text": invalid_machine}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["authorized"] is True
        assert data["ticket_id"] is None
        assert "no" in data["response_text"].lower()
