"""MCP server exposing DevBox CLI operations for agents."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from mcp.server.fastmcp import FastMCP

from . import utils
from .devbox_manager import DevBoxManager
from .launch import launch_devbox


logger = logging.getLogger(__name__)

mcp = FastMCP("DevBox", json_response=True)


def _resolve_termination_target(
    manager: DevBoxManager, identifier: str
) -> Tuple[Optional[str], Optional[str]]:
    """Resolve instance id and project name for a terminate request.

    Parameters
    ----------
    manager : DevBoxManager
        Manager used to query existing instances.
    identifier : str
        Project name or instance id provided by the caller.

    Returns
    -------
    tuple
        Instance id and project name when resolvable, otherwise None values.
    """
    instances = manager.list_instances(project=identifier)
    if len(instances) == 1:
        return instances[0].get("InstanceId"), instances[0].get("Project")
    if len(instances) > 1:
        return None, None

    try:
        response = manager.ec2.describe_instances(InstanceIds=[identifier])
        instance = response["Reservations"][0]["Instances"][0]
        project = utils.get_project_tag(instance.get("Tags", [])) or None
        return instance.get("InstanceId"), project
    except Exception:
        return None, None


@mcp.tool()
def devbox_launch(
    project: str,
    instance_type: Optional[str] = None,
    key_pair: Optional[str] = None,
    volume_size: int = 0,
    base_ami: Optional[str] = None,
    param_prefix: str = "/devbox",
) -> Dict[str, Any]:
    """Launch a devbox instance and return structured details.

    Parameters
    ----------
    project : str
        Project name (alphanumeric and hyphens only).
    instance_type : str, optional
        EC2 instance type to use.
    key_pair : str, optional
        EC2 key pair name for SSH access.
    volume_size : int
        Minimum size (GiB) for the root EBS volume.
    base_ami : str, optional
        Base AMI ID for new projects.
    param_prefix : str
        SSM parameter prefix.

    Returns
    -------
    dict
        Structured launch result including instance identifiers and status.

    Raises
    ------
    RuntimeError
        If the launch fails.
    """
    try:
        return launch_devbox(
            project=project,
            instance_type=instance_type,
            key_pair=key_pair,
            volume_size=volume_size,
            base_ami=base_ami,
            param_prefix=param_prefix,
            emit_output=False,
        )
    except Exception as e:
        logger.exception("devbox_launch failed")
        raise RuntimeError(f"Failed to launch devbox: {e}") from e


@mcp.tool()
def devbox_status(project: Optional[str] = None) -> Dict[str, Any]:
    """Return status for instances, volumes, and snapshots.

    Parameters
    ----------
    project : str, optional
        Optional project name to filter resources.

    Returns
    -------
    dict
        Lists of instances, volumes, and snapshots.

    Raises
    ------
    RuntimeError
        If status retrieval fails.
    """
    try:
        manager = DevBoxManager()
        instances = manager.list_instances(project=project, serialize=True)
        volumes = manager.list_volumes(project=project)
        snapshots = manager.list_snapshots(project=project, serialize=True)
        return {
            "instances": instances,
            "volumes": volumes,
            "snapshots": snapshots,
        }
    except Exception as e:
        logger.exception("devbox_status failed")
        raise RuntimeError(f"Failed to retrieve status: {e}") from e


@mcp.tool()
def devbox_terminate(identifier: str) -> Dict[str, Any]:
    """Terminate a devbox instance by project name or instance id.

    Parameters
    ----------
    identifier : str
        Project name or instance id to terminate.

    Returns
    -------
    dict
        Termination result including success flag and resolved identifiers.

    Raises
    ------
    RuntimeError
        If termination fails.
    """
    try:
        manager = DevBoxManager()
        instance_id, project = _resolve_termination_target(manager, identifier)
        success, message = manager.terminate_instance(identifier)
        return {
            "success": success,
            "message": message,
            "project": project,
            "instance_id": instance_id,
        }
    except Exception as e:
        logger.exception("devbox_terminate failed")
        raise RuntimeError(f"Failed to terminate instance: {e}") from e


def run_mcp_server() -> None:
    """Run the MCP server over stdio transport.

    Returns
    -------
    None
        Runs the MCP server event loop.
    """
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting DevBox MCP server (stdio)")
    mcp.run(transport="stdio")
