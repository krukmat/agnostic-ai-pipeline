import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from scripts.orchestrate import main as orchestrate_main
from a2a.executors import LocalExecutor, RemoteExecutor

@pytest.mark.asyncio
@patch("scripts.orchestrate.load_stories")
@patch("scripts.orchestrate.save_stories")
@patch("scripts.common.load_config")
async def test_orchestrator_local_mode(mock_load_config, mock_save_stories, mock_load_stories):
    """Test orchestrator in local mode."""
    # Arrange
    mock_load_config.return_value = {
        "a2a": {
            "execution_mode": "local",
            "agents": {
                "business_analyst": {"strategy": "local"},
                "product_owner": {"strategy": "local"},
                "architect": {"strategy": "local"},
                "developer": {"strategy": "local"},
                "qa": {"strategy": "local"},
            }
        }
    }
    mock_load_stories.return_value = [{"id": "S1", "status": "todo"}]
    
    with patch("a2a.executors.LocalExecutor") as mock_local_executor, \
         patch("a2a.executors.RemoteExecutor") as mock_remote_executor:
        
        mock_local_executor.return_value = AsyncMock()
        mock_remote_executor.return_value = AsyncMock()

        # Act
        await orchestrate_main()

        # Assert
        assert mock_local_executor.call_count > 0
        assert mock_remote_executor.call_count == 0

@pytest.mark.asyncio
@patch("scripts.orchestrate.load_stories")
@patch("scripts.orchestrate.save_stories")
@patch("scripts.common.load_config")
async def test_orchestrator_remote_mode(mock_load_config, mock_save_stories, mock_load_stories):
    """Test orchestrator in remote mode."""
    # Arrange
    mock_load_config.return_value = {
        "a2a": {
            "execution_mode": "remote",
            "agents": {
                "business_analyst": {"strategy": "remote", "url": "http://localhost:8001"},
                "product_owner": {"strategy": "remote", "url": "http://localhost:8002"},
                "architect": {"strategy": "remote", "url": "http://localhost:8003"},
                "developer": {"strategy": "remote", "url": "http://localhost:8004"},
                "qa": {"strategy": "remote", "url": "http://localhost:8005"},
            }
        }
    }
    mock_load_stories.return_value = [{"id": "S1", "status": "todo"}]
    
    with patch("a2a.executors.LocalExecutor") as mock_local_executor, \
         patch("a2a.executors.RemoteExecutor") as mock_remote_executor:
        
        mock_local_executor.return_value = AsyncMock()
        mock_remote_executor.return_value = AsyncMock()

        # Act
        await orchestrate_main()

        # Assert
        assert mock_remote_executor.call_count > 0
        assert mock_local_executor.call_count > 0 # LocalExecutor is always created as a fallback

@pytest.mark.asyncio
@patch("scripts.orchestrate.load_stories")
@patch("scripts.orchestrate.save_stories")
@patch("scripts.common.load_config")
async def test_orchestrator_mixed_mode(mock_load_config, mock_save_stories, mock_load_stories):
    """Test orchestrator in mixed mode."""
    # Arrange
    mock_load_config.return_value = {
        "a2a": {
            "execution_mode": "auto",
            "agents": {
                "business_analyst": {"strategy": "local"},
                "product_owner": {"strategy": "remote", "url": "http://localhost:8002"},
                "architect": {"strategy": "local"},
                "developer": {"strategy": "remote", "url": "http://localhost:8004"},
                "qa": {"strategy": "local"},
            }
        }
    }
    mock_load_stories.return_value = [{"id": "S1", "status": "todo"}]
    
    with patch("a2a.executors.LocalExecutor") as mock_local_executor, \
         patch("a2a.executors.RemoteExecutor") as mock_remote_executor:
        
        mock_local_executor.return_value = AsyncMock()
        mock_remote_executor.return_value = AsyncMock()

        # Act
        await orchestrate_main()

        # Assert
        assert mock_remote_executor.call_count == 2
        assert mock_local_executor.call_count > 2
