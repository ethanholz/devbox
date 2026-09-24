"""Terminate command helpers shared by the CLI and CLI Lambda."""

from __future__ import annotations

from typing import Any

from ..cli_lambda.contracts import CliRequestEnvelope, build_event
from ..cli_protocol import CliAction, CliEventType
from ..devbox_manager import DevBoxManager
from ..remote_client import invoke_action


def build_terminate_payload(identifier: str) -> dict[str, Any]:
    """Build the remote ``terminate`` request payload.

    Parameters
    ----------
    identifier : str
        Instance ID or project name supplied by the CLI.

    Returns
    -------
    dict[str, Any]
        Action payload ready for the shared remote client.
    """
    return {"identifier": identifier}


def run_terminate_command(
    identifier: str,
    param_prefix: str,
    console: Any,
    json_output: bool = False,
) -> dict[str, Any]:
    """Run the remote ``terminate`` command and render the result.

    Parameters
    ----------
    identifier : str
        Instance ID or project name supplied by the CLI.
    param_prefix : str
        Parameter prefix used to discover the CLI Lambda endpoint.
    console : Any
        Console-like object used to render success messages.
    """
    result = invoke_action(
        action=CliAction.TERMINATE,
        payload=build_terminate_payload(identifier),
        param_prefix=param_prefix,
        console=None if json_output else console,
    )
    if not json_output:
        console.print_success(
            f"Terminating instance {result['instance_id']} (project: {result['project']})."
        )
    return result


def validate_terminate_payload(payload: dict[str, Any]) -> str:
    """Validate and normalize the ``terminate`` action payload.

    Parameters
    ----------
    payload : dict[str, Any]
        Action payload decoded from the request envelope.

    Returns
    -------
    str
        Instance ID or project name to terminate.

    Raises
    ------
    ValueError
        Raised when ``identifier`` is not a non-empty string.
    """
    identifier = payload.get("identifier")
    if not isinstance(identifier, str) or not identifier:
        raise ValueError(
            "The `terminate` payload field `identifier` must be a non-empty string."
        )
    return identifier


def handle_terminate_action(envelope: CliRequestEnvelope) -> list[dict[str, Any]]:
    """Execute the remote ``terminate`` action.

    Parameters
    ----------
    envelope : CliRequestEnvelope
        Validated request envelope for the ``terminate`` action.

    Returns
    -------
    list[dict[str, Any]]
        Result and terminal success events for the NDJSON response stream.
    """
    identifier = validate_terminate_payload(envelope.payload)
    manager_prefix = envelope.param_prefix.strip("/") or "devbox"
    manager = DevBoxManager(prefix=manager_prefix)
    result_data = manager.terminate_instance(identifier)
    return [
        build_event(
            CliEventType.RESULT,
            CliAction.TERMINATE,
            "Termination request accepted",
            result_data,
        ),
        build_event(CliEventType.SUCCESS, CliAction.TERMINATE, "Terminate complete"),
    ]
