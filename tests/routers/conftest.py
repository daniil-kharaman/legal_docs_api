import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from unittest.mock import Mock, MagicMock
from datetime import date
from auth.authentication import pwd_context
from validation import schemas


@pytest.fixture
def mock_db():
    """Create a mock database session"""
    return Mock()


@pytest.fixture
def mock_user():
    """Create a mock user object"""
    user = schemas.UserInDB(
        id=1,
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        password=pwd_context.hash("testpassword123"),
        disabled=False
    )
    return user


@pytest.fixture
def mock_client():
    """Create a mock client object"""
    client = Mock()
    client.id = 1
    client.firstname = "John"
    client.second_name = "Michael"
    client.lastname = "Doe"
    client.birthdate = date(1990, 1, 1)
    client.phone_number = "+4915112534961"
    client.email = "john.doe@example.com"
    client.client_address = None
    return client


@pytest.fixture
def mock_address():
    """Create a mock address object"""
    address = Mock()
    address.id = 1
    address.client_id = 1
    address.house_number = "123"
    address.street = "Main Street"
    address.city = "New York"
    address.postal_code = "10001"
    address.country = "USA"
    address.state = "NY"
    return address


@pytest.fixture
def mock_template():
    """Create a mock template object"""
    template = Mock()
    template.id = 1
    template.template_name = "Test Template"
    template.template_path = "document_templates/1/test_template.docx"
    return template


def override_get_db():
    """Override database dependency for testing"""
    return Mock()


def override_get_current_user(mock_user):
    """Create function to override current user dependency"""
    async def _override():
        return mock_user
    return _override
