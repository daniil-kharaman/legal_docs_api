import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date

from storage.data_manager import (
    DbManager,
    ClientManager,
    AddressManager,
    TemplateManager,
    UserManager,
    TokenManager
)
from storage import db_models
from validation import schemas


class TestDbManager:
    """Tests for the base DbManager class"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session"""
        return Mock()

    @pytest.fixture
    def db_manager(self, mock_db):
        """Create a DbManager instance"""
        return DbManager(
            db=mock_db,
            object_id=1,
            schema=schemas.Client,
            update_schema=schemas.ClientUpdate,
            in_db_schema=schemas.ClientInDb,
            db_model=db_models.Client,
            user_id=10
        )

    def test_get_object(self, db_manager, mock_db):
        """Test retrieving a single object by ID"""
        mock_object = Mock()
        mock_db.get.return_value = mock_object

        result = db_manager.get_object()

        assert result == mock_object
        mock_db.get.assert_called_once()

    def test_add_object(self, db_manager, mock_db):
        """Test adding a new object"""
        mock_pydantic = Mock()
        mock_pydantic.model_dump.return_value = {
            "firstname": "John",
            "lastname": "Doe"
        }

        result = db_manager.add_object(mock_pydantic)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_delete_object(self, db_manager, mock_db):
        """Test deleting an object"""
        mock_object = Mock()
        mock_db.get.return_value = mock_object

        db_manager.delete_object()

        mock_db.delete.assert_called_once_with(mock_object)
        mock_db.commit.assert_called_once()

    def test_update_object(self, db_manager, mock_db):
        """Test updating an existing object"""
        mock_db_object = Mock()
        mock_db.get.return_value = mock_db_object

        mock_new_data = Mock()
        mock_new_data.model_dump.return_value = {"firstname": "Jane"}

        with patch('storage.data_manager.jsonable_encoder') as mock_encoder:
            from datetime import date
            mock_encoder.return_value = {
                "id": 1,
                "firstname": "John",
                "second_name": "Michael",
                "lastname": "Doe",
                "birthdate": date(1990, 1, 1),
                "phone_number": None,
                "email": None,
                "user_id": 10
            }

            result = db_manager.update_object(mock_new_data)

            mock_db.commit.assert_called_once()


class TestClientManager:
    """Tests for the ClientManager class"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session"""
        db = Mock()
        db.query = Mock(return_value=db)
        db.where = Mock(return_value=db)
        db.execute = Mock(return_value=db)
        return db

    @pytest.fixture
    def client_manager(self, mock_db):
        """Create a ClientManager instance"""
        return ClientManager(db=mock_db, object_id=1, user_id=10)

    def test_client_in_database_exists(self, client_manager, mock_db):
        """Test checking if client exists in database"""
        mock_client_data = Mock()
        mock_client_data.firstname = "John"
        mock_client_data.second_name = "Michael"
        mock_client_data.lastname = "Doe"
        mock_client_data.birthdate = date(1990, 1, 1)

        mock_result = Mock()
        mock_db.execute.return_value = mock_result
        mock_result.first.return_value = mock_client_data

        client = schemas.ClientBase(
            firstname="John",
            second_name="Michael",
            lastname="Doe",
            birthdate=date(1990, 1, 1)
        )

        result = client_manager.client_in_database(client)

        assert result == mock_client_data

    def test_client_in_database_not_exists(self, client_manager, mock_db):
        """Test checking if client doesn't exist in database"""
        mock_result = Mock()
        mock_db.execute.return_value = mock_result
        mock_result.first.return_value = None

        client = schemas.ClientBase(
            firstname="Jane",
            second_name="Mary",
            lastname="Smith",
            birthdate=date(1995, 5, 5)
        )

        result = client_manager.client_in_database(client)

        assert result is None


class TestAddressManager:
    """Tests for the AddressManager class"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session"""
        db = Mock()
        db.query = Mock(return_value=db)
        db.where = Mock(return_value=db)
        db.execute = Mock(return_value=db)
        return db

    @pytest.fixture
    def address_manager(self, mock_db):
        """Create an AddressManager instance"""
        return AddressManager(db=mock_db, object_id=1, user_id=10, client_id=5)

    def test_address_relate_to_client(self, address_manager, mock_db):
        """Test retrieving address related to client"""
        mock_address = Mock()
        mock_result = Mock()
        mock_db.execute.return_value = mock_result
        mock_result.first.return_value = mock_address

        result = address_manager.address_relate_to_client()

        assert result == mock_address

    def test_add_object_with_client_id(self, address_manager, mock_db):
        """Test adding address with client_id"""
        mock_address = Mock(spec=schemas.Address)
        mock_address.model_dump.return_value = {
            "house_number": "123",
            "street": "Main St",
            "city": "Boston",
            "postal_code": "02101",
            "country": "USA"
        }

        result = address_manager.add_object(mock_address)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()


class TestTemplateManager:
    """Tests for the TemplateManager class"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session"""
        db = Mock()
        db.query = Mock(return_value=db)
        db.where = Mock(return_value=db)
        db.execute = Mock(return_value=db)
        return db

    @pytest.fixture
    def template_manager(self, mock_db):
        """Create a TemplateManager instance"""
        return TemplateManager(db=mock_db, object_id=1, user_id=10)

    def test_template_in_database_exists(self, template_manager, mock_db):
        """Test checking if template exists by name"""
        mock_template = Mock()
        mock_result = Mock()
        mock_db.execute.return_value = mock_result
        mock_result.first.return_value = mock_template

        result = template_manager.template_in_database("my_template")

        assert result == mock_template

    def test_template_in_database_not_exists(self, template_manager, mock_db):
        """Test checking if template doesn't exist"""
        mock_result = Mock()
        mock_db.execute.return_value = mock_result
        mock_result.first.return_value = None

        result = template_manager.template_in_database("nonexistent_template")

        assert result is None

    def test_template_path_in_db(self, template_manager, mock_db):
        """Test checking if template exists by path"""
        mock_template = Mock()
        mock_result = Mock()
        mock_db.execute.return_value = mock_result
        mock_result.first.return_value = mock_template

        result = template_manager.template_path_in_db("/path/to/template.docx")

        assert result == mock_template


class TestUserManager:
    """Tests for the UserManager class"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session"""
        db = Mock()
        db.query = Mock(return_value=db)
        db.where = Mock(return_value=db)
        db.execute = Mock(return_value=db)
        return db

    @pytest.fixture
    def user_manager(self, mock_db):
        """Create a UserManager instance"""
        return UserManager(db=mock_db, object_id=None)

    def test_user_in_database_by_username(self, user_manager, mock_db):
        """Test finding user by username"""
        mock_user = Mock()
        mock_user.id = 5
        mock_user.username = "testuser"

        mock_result = Mock()
        mock_result.scalars.return_value.first.return_value = mock_user
        mock_db.execute.return_value = mock_result

        result = user_manager.user_in_database("testuser")

        assert result == mock_user

    def test_user_in_database_by_email(self, user_manager, mock_db):
        """Test finding user by email"""
        mock_user = Mock()
        mock_user.id = 7
        mock_user.email = "test@example.com"

        mock_result = Mock()
        mock_result.scalars.return_value.first.return_value = mock_user
        mock_db.execute.return_value = mock_result

        result = user_manager.user_in_database("test@example.com")

        assert result == mock_user

    def test_user_in_database_not_exists(self, user_manager, mock_db):
        """Test when user doesn't exist"""
        mock_result = Mock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = mock_result

        result = user_manager.user_in_database("nonexistent")

        assert result is None

    @patch('storage.data_manager.pwd_context')
    def test_add_object_hashes_password(self, mock_pwd_context, user_manager, mock_db):
        """Test that password is hashed when adding user"""
        mock_pwd_context.hash.return_value = "hashed_password"

        mock_user_create = Mock(spec=schemas.UserCreate)
        mock_user_create.model_dump.return_value = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "plain_password"
        }

        result = user_manager.add_object(mock_user_create)

        mock_pwd_context.hash.assert_called_once_with("plain_password")
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @patch('storage.data_manager.pwd_context')
    @patch('storage.data_manager.jsonable_encoder')
    def test_update_object_hashes_new_password(self, mock_encoder, mock_pwd_context, user_manager, mock_db):
        """Test that new password is hashed when updating user"""
        mock_pwd_context.hash.return_value = "hashed_new_password"

        mock_db_user = Mock()
        mock_db.get.return_value = mock_db_user

        mock_encoder.return_value = {
            "id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "password": "old_hash",
            "disabled": False
        }

        mock_update_data = Mock(spec=schemas.UserUpdate)
        mock_update_data.password = "new_password"
        mock_update_data.model_dump.return_value = {"password": "hashed_new_password"}

        result = user_manager.update_object(mock_update_data)

        mock_pwd_context.hash.assert_called_once_with("new_password")
        mock_db.commit.assert_called_once()


class TestTokenManager:
    """Tests for the TokenManager class"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session"""
        db = Mock()
        db.query = Mock(return_value=db)
        db.where = Mock(return_value=db)
        return db

    @pytest.fixture
    def token_manager(self, mock_db):
        """Create a TokenManager instance"""
        return TokenManager(db=mock_db, object_id=1, user_id=10)

    def test_get_object_by_name_exists(self, token_manager, mock_db):
        """Test retrieving token by name when it exists"""
        mock_token = Mock()
        mock_token.token_name = "google_auth"
        mock_token.user_id = 10

        mock_query = Mock()
        mock_query.first.return_value = mock_token
        mock_db.query.return_value.where.return_value = mock_query

        result = token_manager.get_object_by_name("google_auth")

        assert result == mock_token

    def test_get_object_by_name_not_exists(self, token_manager, mock_db):
        """Test retrieving token by name when it doesn't exist"""
        mock_query = Mock()
        mock_query.first.return_value = None
        mock_db.query.return_value.where.return_value = mock_query

        result = token_manager.get_object_by_name("nonexistent_token")

        assert result is None
