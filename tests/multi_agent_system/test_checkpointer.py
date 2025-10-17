import pytest
from unittest.mock import patch, Mock, AsyncMock
from multi_agent_system import (
    get_checkpointer,
    close_checkpointer,
    CheckpointerError
)


class TestGetCheckpointer:
    """Tests for get_checkpointer function"""

    @pytest.mark.asyncio
    @patch('multi_agent_system.database.AsyncPostgresSaver')
    @patch('multi_agent_system.database.AsyncConnectionPool')
    async def test_get_checkpointer_first_call(self, mock_pool_class, mock_saver_class, mock_env_vars):
        """Test creating checkpointer on first call"""
        with patch.dict('os.environ', mock_env_vars):
            # Reset global state
            import multi_agent_system.database as ss
            ss._connection_pool = None
            ss._checkpointer = None

            # Mock connection pool
            mock_pool = AsyncMock()
            mock_pool_class.return_value = mock_pool

            # Mock checkpointer
            mock_cp = AsyncMock()
            mock_cp.setup = AsyncMock()
            mock_saver_class.return_value = mock_cp

            result = await get_checkpointer()

            assert result == mock_cp
            mock_pool_class.assert_called_once()
            mock_saver_class.assert_called_once_with(mock_pool)
            mock_cp.setup.assert_called_once()

    @pytest.mark.asyncio
    @patch('multi_agent_system.database.AsyncPostgresSaver')
    @patch('multi_agent_system.database.AsyncConnectionPool')
    async def test_get_checkpointer_reuses_existing(self, mock_pool_class, mock_saver_class, mock_env_vars):
        """Test reusing existing checkpointer"""
        with patch.dict('os.environ', mock_env_vars):
            # Set up pre-existing checkpointer
            import multi_agent_system.database as ss
            mock_existing_cp = AsyncMock()
            ss._checkpointer = mock_existing_cp

            result = await get_checkpointer()

            assert result == mock_existing_cp
            # Should not create new pool or checkpointer
            mock_pool_class.assert_not_called()
            mock_saver_class.assert_not_called()

    @pytest.mark.asyncio
    @patch('multi_agent_system.database.AsyncPostgresSaver')
    @patch('multi_agent_system.database.AsyncConnectionPool')
    async def test_get_checkpointer_pool_creation_error(self, mock_pool_class, mock_saver_class, mock_env_vars):
        """Test handling pool creation error"""
        with patch.dict('os.environ', mock_env_vars):
            # Reset global state
            import multi_agent_system.database as ss
            ss._connection_pool = None
            ss._checkpointer = None

            mock_pool_class.side_effect = Exception("Pool creation failed")

            with pytest.raises(CheckpointerError, match="Error while getting the database connection"):
                await get_checkpointer()

    @pytest.mark.asyncio
    @patch('multi_agent_system.database.AsyncPostgresSaver')
    @patch('multi_agent_system.database.AsyncConnectionPool')
    async def test_get_checkpointer_setup_error(self, mock_pool_class, mock_saver_class, mock_env_vars):
        """Test handling checkpointer setup error"""
        with patch.dict('os.environ', mock_env_vars):
            # Reset global state
            import multi_agent_system.database as ss
            ss._connection_pool = None
            ss._checkpointer = None

            # Mock connection pool
            mock_pool = AsyncMock()
            mock_pool_class.return_value = mock_pool

            # Mock checkpointer with setup error
            mock_cp = AsyncMock()
            mock_cp.setup = AsyncMock(side_effect=Exception("Setup failed"))
            mock_saver_class.return_value = mock_cp

            with pytest.raises(CheckpointerError, match="Error while getting the database connection"):
                await get_checkpointer()

    @pytest.mark.asyncio
    @patch('multi_agent_system.database.AsyncPostgresSaver')
    @patch('multi_agent_system.database.AsyncConnectionPool')
    async def test_get_checkpointer_with_existing_pool(self, mock_pool_class, mock_saver_class, mock_env_vars):
        """Test creating checkpointer with existing pool"""
        with patch.dict('os.environ', mock_env_vars):
            # Set up pre-existing pool
            import multi_agent_system.database as ss
            mock_existing_pool = AsyncMock()
            ss._connection_pool = mock_existing_pool
            ss._checkpointer = None

            # Mock checkpointer
            mock_cp = AsyncMock()
            mock_cp.setup = AsyncMock()
            mock_saver_class.return_value = mock_cp

            result = await get_checkpointer()

            assert result == mock_cp
            # Should not create new pool
            mock_pool_class.assert_not_called()
            # Should use existing pool
            mock_saver_class.assert_called_once_with(mock_existing_pool)


class TestCloseCheckpointer:
    """Tests for close_checkpointer function"""

    @pytest.mark.asyncio
    async def test_close_checkpointer_success(self):
        """Test successful checkpointer close"""
        import multi_agent_system.database as ss
        mock_pool = AsyncMock()
        mock_pool.close = AsyncMock()
        ss._connection_pool = mock_pool

        await close_checkpointer()

        mock_pool.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_checkpointer_no_pool(self):
        """Test closing when no pool exists"""
        import multi_agent_system.database as ss
        ss._connection_pool = None

        # Should not raise exception
        await close_checkpointer()

    @pytest.mark.asyncio
    async def test_close_checkpointer_error_handling(self):
        """Test error handling during close"""
        import multi_agent_system.database as ss
        mock_pool = AsyncMock()
        mock_pool.close = AsyncMock(side_effect=Exception("Close error"))
        ss._connection_pool = mock_pool

        # Should not raise exception, just log error
        await close_checkpointer()