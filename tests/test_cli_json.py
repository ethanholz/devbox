"""JSON output of the Click CLI."""

import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from devbox.cli import cli


def test_status_json_keeps_remote_timestamps_and_empty_collections():
    payload = {
        "instances": [{"InstanceId": "i-123", "LaunchTime": "2026-03-30T20:30:00+00:00"}],
        "volumes": [],
        "snapshots": [],
    }
    with patch("devbox.commands.status.invoke_action", return_value=payload) as invoke:
        result = CliRunner().invoke(cli, ["--json", "status", "demo"])

    assert result.exit_code == 0
    assert json.loads(result.stdout) == payload
    assert result.stderr == ""
    assert invoke.call_args.kwargs["console"] is None


def test_terminate_json_after_command():
    payload = {"instance_id": "i-123", "project": "demo"}
    with patch("devbox.commands.terminate.invoke_action", return_value=payload):
        result = CliRunner().invoke(cli, ["terminate", "demo", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.stdout) == payload
    assert result.stderr == ""


def test_json_errors_leave_stdout_clean():
    with patch("devbox.commands.status.invoke_action", side_effect=RuntimeError("offline")):
        result = CliRunner().invoke(cli, ["status", "--json"])

    assert result.exit_code == 1
    assert result.stdout == ""
    assert json.loads(result.stderr) == {"error": "Failed to retrieve status: offline"}


@pytest.mark.parametrize("args,expected", [
    (["--json", "launch"], "Missing argument 'PROJECT'"),
    (["launch", "--json"], "Missing argument 'PROJECT'"),
    (["status", "--json", "--unknown"], "No such option"),
    (["--json", "unknown"], "No such command 'unknown'"),
    (["--json", "new", "demo"], "Missing option '--base-ami'"),
    (["status", "--param-prefix", "bad//prefix", "--json"],
     "Parameter prefix cannot contain consecutive slashes"),
])
def test_json_click_parsing_errors(args, expected):
    result = CliRunner().invoke(cli, args)

    assert result.exit_code == 2
    assert result.stdout == ""
    assert expected in json.loads(result.stderr)["error"]
    if "--unknown" in args:
        assert "--unknown" in json.loads(result.stderr)["error"]


def test_default_click_parsing_errors_remain_human_readable():
    result = CliRunner().invoke(cli, ["launch"])

    assert result.exit_code == 2
    assert "Usage:" in result.stderr


def test_launch_json_errors_leave_stdout_clean():
    with patch("devbox.launch.launch_programmatic", side_effect=ValueError("bad project")):
        result = CliRunner().invoke(cli, ["launch", "demo", "--json"])

    assert result.exit_code == 1
    assert result.stdout == ""
    assert json.loads(result.stderr) == {"error": "Failed to launch instance: bad project"}


def test_launch_and_new_json_do_not_mix_progress_with_result():
    details = {
        "project": "demo", "instance_id": "i-123", "public_ip": "1.2.3.4",
        "private_ip": "10.0.0.4", "public_dns": "ec2.example.amazonaws.com",
        "dns": "demo.example.com", "ssh_username": "ubuntu",
        "ssh_command": "ssh -i /path/to/your-key.pem ubuntu@1.2.3.4",
    }
    with patch("devbox.launch.launch_programmatic") as launch:
        launch.side_effect = lambda **kwargs: (print("Launching..."), details)[1]
        result = CliRunner().invoke(cli, ["launch", "demo", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout) == details
    assert "Launching..." in result.stderr

    with patch("devbox.new.new_project_programmatic") as new:
        new.side_effect = lambda **kwargs: (print("Creating..."), {
            "project": kwargs["project"], "status": "READY"
        })[1]
        result = CliRunner().invoke(cli, ["--json", "new", "demo", "--base-ami", "ami-12345678"])
    assert result.exit_code == 0
    assert json.loads(result.stdout) == {"project": "demo", "status": "READY"}
    assert "Creating..." in result.stderr


def test_delete_project_json_requires_force():
    with patch("devbox.cli.DevBoxManager") as manager_class:
        manager = manager_class.return_value
        manager.get_project_item.return_value = {"AMI": "ami-123"}
        manager.project_in_use.return_value = (False, "")
        manager.delete_ami_and_snapshots.return_value = {
            "ami_id": "ami-123", "snapshot_count": 2
        }
        result = CliRunner().invoke(cli, ["delete-project", "demo", "--force", "--json"])
        assert result.exit_code == 0
        assert json.loads(result.stdout) == {
            "project": "demo", "deleted": True, "ami_id": "ami-123", "snapshot_count": 2
        }
        assert result.stderr == ""

        result = CliRunner().invoke(cli, ["--json", "delete-project", "demo"], input="n\n")
        assert result.exit_code == 2
        assert result.stdout == ""
        assert json.loads(result.stderr) == {"error": "--json requires --force for delete-project"}
