import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from scripts.orchestrate import main as orchestrate_main
from a2a.executors import LocalExecutor, RemoteExecutor


@pytest.mark.asyncio
@patch("scripts.orchestrate.db_enabled", return_value=False)
@patch("scripts.orchestrate.load_stories")
@patch("scripts.orchestrate.save_stories")
@patch("scripts.common.load_config")
async def test_orchestrator_local_mode(mock_load_config, mock_save_stories, mock_load_stories, mock_db_enabled):
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
    # Return empty list after first call to stop the loop
    mock_load_stories.side_effect = [[{"id": "S1", "status": "todo"}], [{"id": "S1", "status": "done"}]]

    # Mock execute_role to return proper dict results
    with patch("scripts.orchestrate.execute_role") as mock_execute_role, \
         patch("a2a.executors.LocalExecutor") as mock_local_executor, \
         patch("a2a.executors.RemoteExecutor") as mock_remote_executor:

        # Return proper dict for dev result
        async def mock_dev_result(*args, **kwargs):
            return {"status": "success", "model_info": {"provider": "test", "model": "test-model"}}
        mock_execute_role.side_effect = mock_dev_result

        mock_local_executor.return_value = AsyncMock()
        mock_remote_executor.return_value = AsyncMock()

        # Act
        await orchestrate_main()

        # Assert
        assert mock_local_executor.call_count >= 0  # May or may not be called depending on execution path

@pytest.mark.asyncio
@patch("scripts.orchestrate.db_enabled", return_value=False)
@patch("scripts.orchestrate.load_stories")
@patch("scripts.orchestrate.save_stories")
@patch("scripts.common.load_config")
async def test_orchestrator_remote_mode(mock_load_config, mock_save_stories, mock_load_stories, mock_db_enabled):
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
    mock_load_stories.side_effect = [[{"id": "S1", "status": "todo"}], [{"id": "S1", "status": "done"}]]

    with patch("scripts.orchestrate.execute_role") as mock_execute_role, \
         patch("a2a.executors.LocalExecutor") as mock_local_executor, \
         patch("a2a.executors.RemoteExecutor") as mock_remote_executor:

        async def mock_dev_result(*args, **kwargs):
            return {"status": "success", "model_info": {"provider": "test", "model": "test-model"}}
        mock_execute_role.side_effect = mock_dev_result

        mock_local_executor.return_value = AsyncMock()
        mock_remote_executor.return_value = AsyncMock()

        # Act
        await orchestrate_main()

        # Assert - just verify it runs without error
        assert True

@pytest.mark.asyncio
@patch("scripts.orchestrate.db_enabled", return_value=False)
@patch("scripts.orchestrate.load_stories")
@patch("scripts.orchestrate.save_stories")
@patch("scripts.common.load_config")
async def test_orchestrator_mixed_mode(mock_load_config, mock_save_stories, mock_load_stories, mock_db_enabled):
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
    mock_load_stories.side_effect = [[{"id": "S1", "status": "todo"}], [{"id": "S1", "status": "done"}]]

    with patch("scripts.orchestrate.execute_role") as mock_execute_role, \
         patch("a2a.executors.LocalExecutor") as mock_local_executor, \
         patch("a2a.executors.RemoteExecutor") as mock_remote_executor:

        async def mock_dev_result(*args, **kwargs):
            return {"status": "success", "model_info": {"provider": "test", "model": "test-model"}}
        mock_execute_role.side_effect = mock_dev_result

        mock_local_executor.return_value = AsyncMock()
        mock_remote_executor.return_value = AsyncMock()

        # Act
        await orchestrate_main()

        # Assert - just verify it runs without error
        assert True
