import json
import time
import uuid

from pathlib import Path

from browser_bridge_server import (
    ensure_server_started,
    submit_command,
)


ROOT_DIR = Path(__file__).resolve().parents[1]

BRIDGE_CONFIG_FILE = (
    ROOT_DIR
    / "config"
    / "browser_bridge.json"
)

DEFAULT_TIMEOUT_SECONDS = 12.0
MAX_RESPONSE_BYTES = 256 * 1024
MAX_URL_LENGTH = 4096

HARD_ALLOWED_ACTIONS = {
    "ping",
    "list_tabs",
    "close_site",
    "activate_site",
}


def load_bridge_config():
    try:
        with open(
            BRIDGE_CONFIG_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)
    except (
        OSError,
        json.JSONDecodeError,
    ):
        return {}

    if not isinstance(data, dict):
        return {}

    if data.get("schema_version") != 1:
        return {}

    if not data.get(
        "enabled",
        False,
    ):
        return {}

    host = data.get("host")
    port = data.get("port")
    token = data.get("token")
    extension_id = data.get("extension_id")

    if host != "127.0.0.1":
        return {}

    try:
        port = int(port)
    except (TypeError, ValueError):
        return {}

    if not (1024 <= port <= 65535):
        return {}

    if not isinstance(token, str) or len(token) < 64:
        return {}

    if (
        not isinstance(extension_id, str)
        or len(extension_id) != 32
        or not extension_id.isalpha()
        or extension_id.lower() != extension_id
    ):
        return {}

    data["port"] = port

    maximum_body = data.get(
        "maximum_body_bytes",
        MAX_RESPONSE_BYTES,
    )

    try:
        maximum_body = int(
            maximum_body
        )
    except (TypeError, ValueError):
        maximum_body = MAX_RESPONSE_BYTES

    data["maximum_body_bytes"] = max(
        4096,
        min(
            maximum_body,
            MAX_RESPONSE_BYTES,
        ),
    )

    return data


def is_bridge_configured():
    return bool(
        load_bridge_config()
    )


def _prepare_server():
    config = load_bridge_config()

    if not config:
        return (
            False,
            None,
            (
                "Le pont Edge local n'est pas configuré. "
                "Exécute .\\agent_tools\\edge_bridge\\setup_edge_bridge.py "
                "puis recharge l'extension dans edge://extensions/."
            ),
        )

    success, error = ensure_server_started(
        config
    )

    if not success:
        return False, None, error

    return True, config, None


def bridge_request(
    action,
    payload=None,
    timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
):
    if not isinstance(action, str):
        return False, None, "Action de pont invalide."

    action = action.strip()

    if action not in HARD_ALLOWED_ACTIONS:
        return False, None, "Action de pont non autorisée."

    if payload is None:
        payload = {}

    if not isinstance(payload, dict):
        return False, None, "Paramètres de pont invalides."

    success, config, error = _prepare_server()

    if not success:
        return False, None, error

    try:
        timeout_seconds = float(
            timeout_seconds
        )
    except (TypeError, ValueError):
        timeout_seconds = DEFAULT_TIMEOUT_SECONDS

    timeout_seconds = max(
        2.0,
        min(
            timeout_seconds,
            30.0,
        ),
    )

    command = {
        "type": "command",
        "schema_version": 1,
        "request_id": uuid.uuid4().hex,
        "action": action,
        "payload": payload,
        "created_at": time.time(),
    }

    delivered, response, error = submit_command(
        command,
        timeout_seconds,
    )

    if not delivered:
        return False, None, error

    if not isinstance(response, dict):
        return False, None, "Réponse du pont Edge invalide."

    if response.get("type") != "result":
        return False, None, "Réponse du pont Edge invalide."

    if response.get("request_id") != command["request_id"]:
        return False, None, "Réponse du pont Edge non corrélée."

    if response.get("action") != action:
        return False, None, "Action de réponse du pont incohérente."

    success = bool(
        response.get(
            "ok",
            False,
        )
    )

    message = response.get(
        "message"
    )

    if not isinstance(message, str):
        message = (
            "Pont Edge AgentLocal opérationnel."
            if success
            else
            "Le pont Edge a refusé la commande."
        )

    return success, response, message


def close_site_via_bridge(
    url,
    close_all=False,
    maximum_tabs=10,
    allow_subdomains=False,
    timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
):
    if not isinstance(url, str):
        return False, 0, "URL invalide."

    url = url.strip()

    if not url or len(url) > MAX_URL_LENGTH:
        return False, 0, "URL invalide."

    try:
        maximum_tabs = int(
            maximum_tabs
        )
    except (TypeError, ValueError):
        maximum_tabs = 1

    maximum_tabs = max(
        1,
        min(
            maximum_tabs,
            10,
        ),
    )

    success, response, message = bridge_request(
        "close_site",
        {
            "url": url,
            "close_all": bool(
                close_all
            ),
            "maximum_tabs": maximum_tabs,
            "allow_subdomains": bool(
                allow_subdomains
            ),
        },
        timeout_seconds=timeout_seconds,
    )

    if not success:
        return False, 0, message

    count = response.get(
        "closed_count",
        0,
    ) if isinstance(
        response,
        dict
    ) else 0

    try:
        count = int(
            count
        )
    except (TypeError, ValueError):
        count = 0

    count = max(
        0,
        min(
            count,
            10,
        ),
    )

    return True, count, message


def list_tabs_via_bridge(
    timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
):
    success, response, message = bridge_request(
        "list_tabs",
        {},
        timeout_seconds=timeout_seconds,
    )

    if not success:
        return False, [], message

    tabs = response.get(
        "tabs",
        [],
    )

    if not isinstance(
        tabs,
        list
    ):
        tabs = []

    safe_tabs = []

    for item in tabs[:50]:
        if not isinstance(
            item,
            dict
        ):
            continue

        url = item.get(
            "url"
        )

        title = item.get(
            "title"
        )

        if not isinstance(
            url,
            str
        ):
            continue

        safe_tabs.append(
            {
                "url": url[:MAX_URL_LENGTH],
                "title": (
                    title[:500]
                    if isinstance(
                        title,
                        str
                    )
                    else ""
                ),
                "active": bool(
                    item.get(
                        "active",
                        False,
                    )
                ),
            }
        )

    return True, safe_tabs, message


def activate_site_via_bridge(
    url,
    allow_subdomains=False,
    timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
):
    if not isinstance(url, str):
        return False, "URL invalide."

    url = url.strip()

    if not url or len(url) > MAX_URL_LENGTH:
        return False, "URL invalide."

    success, _, message = bridge_request(
        "activate_site",
        {
            "url": url,
            "allow_subdomains": bool(
                allow_subdomains
            ),
        },
        timeout_seconds=timeout_seconds,
    )

    return success, message
