"""Unit tests for devbox MCP server."""

from unittest.mock import MagicMock, patch

import pytest

from devbox.mcp_server import devbox_launch, devbox_status, devbox_terminate


def test_devbox_launch_delegates_to_launch_devbox():
    with patch("devbox.mcp_server.launch_devbox") as mock_launch:
        mock_launch.return_value = {
            "project": "test-project",
            "instance_id": "i-12345",
            "public_ip": "1.2.3.4",
            "username": "ubuntu",
            "image_id": "ami-12345",
            "instance_type": "t3.medium",
            "key_pair": "test-key",
            "status": "running",
        }

        result = devbox_launch(
            "test-project",
            instance_type="t3.medium",
            key_pair="test-key",
        )

        mock_launch.assert_called_once()
        assert result["instance_id"] == "i-12345"
        assert result["project"] == "test-project"


@patch("devbox.mcp_server.DevBoxManager")
def test_devbox_status_returns_structured_results(mock_manager_class):
    manager = MagicMock()
    manager.list_instances.return_value = [{"InstanceId": "i-1"}]
    manager.list_volumes.return_value = [{"VolumeId": "vol-1"}]
    manager.list_snapshots.return_value = [{"SnapshotId": "snap-1"}]
    mock_manager_class.return_value = manager

    result = devbox_status("my-project")

    manager.list_instances.assert_called_once_with(project="my-project", serialize=True)
    manager.list_volumes.assert_called_once_with(project="my-project")
    manager.list_snapshots.assert_called_once_with(project="my-project", serialize=True)
    assert result["instances"] == [{"InstanceId": "i-1"}]
    assert result["volumes"] == [{"VolumeId": "vol-1"}]
    assert result["snapshots"] == [{"SnapshotId": "snap-1"}]


@patch("devbox.mcp_server._resolve_termination_target")
@patch("devbox.mcp_server.DevBoxManager")
def test_devbox_terminate_returns_details(mock_manager_class, mock_resolve):
    manager = MagicMock()
    manager.terminate_instance.return_value = (True, "Terminating")
    mock_manager_class.return_value = manager
    mock_resolve.return_value = ("i-12345", "my-project")

    result = devbox_terminate("my-project")

    manager.terminate_instance.assert_called_once_with("my-project")
    assert result["success"] is True
    assert result["instance_id"] == "i-12345"
    assert result["project"] == "my-project"


@patch("devbox.mcp_server.DevBoxManager")
def test_devbox_status_surfaces_errors(mock_manager_class):
    manager = MagicMock()
    manager.list_instances.side_effect = Exception("Boom")
    mock_manager_class.return_value = manager

    with pytest.raises(RuntimeError):
        devbox_status()
