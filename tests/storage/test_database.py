import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import exc

from storage.database import (
    DatabaseError,
    create_tables,
    get_db,
    get_db_session
)


class TestCreateTables:
    """Tests for the create_tables function"""

    @patch('storage.database.Base')
    @patch('storage.database.engine')
    def test_create_tables_success(self, mock_engine, mock_base):
        """Test successful table creation"""
        mock_metadata = Mock()
        mock_base.metadata = mock_metadata

        create_tables()

        mock_metadata.create_all.assert_called_once_with(bind=mock_engine)

    @patch('storage.database.Base')
    @patch('storage.database.engine')
    def test_create_tables_operational_error(self, mock_engine, mock_base, capsys):
        """Test handling of operational errors during table creation"""
        mock_metadata = Mock()
        mock_metadata.create_all.side_effect = exc.OperationalError("statement", {}, Exception("connection failed"))
        mock_base.metadata = mock_metadata

        create_tables()

        captured = capsys.readouterr()
        assert "Database cannot be accessed" in captured.out

    @patch('storage.database.Base')
    @patch('storage.database.engine')
    def test_create_tables_argument_error(self, mock_engine, mock_base, capsys):
        """Test handling of argument errors during table creation"""
        mock_metadata = Mock()
        mock_metadata.create_all.side_effect = exc.ArgumentError("Invalid argument")
        mock_base.metadata = mock_metadata

        create_tables()

        captured = capsys.readouterr()
        assert "Database cannot be accessed" in captured.out


class TestGetDb:
    """Tests for the get_db generator function"""

    @patch('storage.database.SessionLocal')
    def test_get_db_success(self, mock_session_local):
        """Test successful database session creation"""
        mock_session = Mock()
        mock_session_local.return_value = mock_session

        generator = get_db()
        session = next(generator)

        assert session == mock_session
        mock_session_local.assert_called_once()

        # Clean up generator
        try:
            next(generator)
        except StopIteration:
            pass

        mock_session.close.assert_called_once()

    @patch('storage.database.SessionLocal')
    def test_get_db_operational_error(self, mock_session_local):
        """Test handling of operational error in get_db"""
        mock_session = Mock()
        mock_session_local.return_value = mock_session

        generator = get_db()
        db = next(generator)

        # Simulate an operational error occurring during usage
        try:
            generator.throw(exc.OperationalError("statement", {}, Exception("connection failed")))
        except (DatabaseError, exc.OperationalError):
            # Either exception is acceptable
            pass

        mock_session.close.assert_called()

    @patch('storage.database.SessionLocal')
    def test_get_db_closes_session_on_error(self, mock_session_local):
        """Test that session is closed even when error occurs"""
        mock_session = Mock()
        mock_session_local.return_value = mock_session

        generator = get_db()
        session = next(generator)

        # Simulate an error and close the generator
        try:
            generator.throw(Exception("Test error"))
        except Exception:
            pass

        mock_session.close.assert_called()


class TestGetDbSession:
    """Tests for the get_db_session context manager"""

    @patch('storage.database.SessionLocal')
    def test_get_db_session_success(self, mock_session_local):
        """Test successful database session with context manager"""
        mock_session = Mock()
        mock_session_local.return_value = mock_session

        with get_db_session() as session:
            assert session == mock_session

        mock_session_local.assert_called_once()
        mock_session.close.assert_called_once()

    @patch('storage.database.SessionLocal')
    def test_get_db_session_operational_error(self, mock_session_local):
        """Test handling of operational error in context manager"""
        mock_session = Mock()
        mock_session_local.return_value = mock_session

        with pytest.raises(DatabaseError, match="Database server is unavailable"):
            with get_db_session() as session:
                raise exc.OperationalError("statement", {}, Exception("connection failed"))

        mock_session.close.assert_called_once()

    @patch('storage.database.SessionLocal')
    def test_get_db_session_argument_error(self, mock_session_local):
        """Test handling of argument error in context manager"""
        mock_session = Mock()
        mock_session_local.return_value = mock_session

        with pytest.raises(DatabaseError, match="Database configuration is invalid"):
            with get_db_session() as session:
                raise exc.ArgumentError("Invalid configuration")

        mock_session.close.assert_called_once()

    @patch('storage.database.SessionLocal')
    def test_get_db_session_closes_on_success(self, mock_session_local):
        """Test that session is closed after successful operations"""
        mock_session = Mock()
        mock_session_local.return_value = mock_session

        with get_db_session() as session:
            # Perform some operations
            result = session.query(Mock())

        assert mock_session.close.called

    @patch('storage.database.SessionLocal')
    def test_get_db_session_closes_on_exception(self, mock_session_local):
        """Test that session is closed even after exceptions"""
        mock_session = Mock()
        mock_session_local.return_value = mock_session

        with pytest.raises(ValueError):
            with get_db_session() as session:
                raise ValueError("Custom error")

        mock_session.close.assert_called_once()
