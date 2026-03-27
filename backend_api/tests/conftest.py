import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.main import app
from app.auth import hash_password, create_access_token


def make_cursor_mock(data):
    """Create a mock cursor that supports chaining methods."""
    cursor = MagicMock()
    cursor.sort.return_value = cursor
    cursor.skip.return_value = cursor
    cursor.limit.return_value = cursor
    cursor.to_list = AsyncMock(return_value=data)
    return cursor


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def valid_token():
    return create_access_token({"sub": "testadmin"})


@pytest.fixture
def auth_headers(valid_token):
    return {"Authorization": f"Bearer {valid_token}"}


@pytest.fixture
def test_admin_doc():
    return {
        "_id": "507f1f77bcf86cd799439011",
        "username": "admin",
        "password_hash": hash_password("Monday001!")
    }


@pytest.fixture
def test_user_doc():
    return {
        "_id": "507f1f77bcf86cd799439012",
        "name": "Test User",
        "phone_number": "+1234567890",
        "active": True,
        "created_at": datetime.utcnow()
    }


@pytest.fixture
def test_machine_doc():
    return {
        "_id": "507f1f77bcf86cd799439013",
        "machine_id": "MACH-001",
        "name": "Test Machine",
        "location": "Building A",
        "created_at": datetime.utcnow()
    }


@pytest.fixture
def test_ticket_doc(test_machine_doc):
    return {
        "_id": "507f1f77bcf86cd799439014",
        "machine_id": test_machine_doc["machine_id"],
        "status": "open",
        "description": "Test ticket",
        "created_by": "admin",
        "created_at": datetime.utcnow(),
        "assigned_to": "+1234567890"
    }
