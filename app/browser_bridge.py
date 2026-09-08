import json
import os
import secrets
import time
import uuid

from pathlib import Path


HOST_NAME = "com.agentlocal.bridge"
BRIDGE_DIR_NAME = "AgentLocalBridge"
CONFIG_FILE_NAME = "bridge_config.json"
COMMAND_FILE_NAME = "command.json"
INFLIGHT_FILE_NAME = "command.inflight.json"
RESPONSE_FILE_NAME = "response.json"
LOCK_FILE_NAME = "agent.lock"

DEFAULT_TIMEOUT_SECONDS = 5.0
MAX_RESPONSE_BYTES = 256 * 1024
MAX_URL_LENGTH = 4096


def get_bridge_dir():
    local_appdata = os.environ.get("LOCALAPPDATA")

    if local_appdata:
        base = Path(local_appdata)
    else:
        base = Path.home() / "AppData" / "Local"

    return base / BRIDGE_DIR_NAME


def get_bridge_paths():
    bridge_dir = get_bridge_dir()

    return {
        "dir": bridge_dir,
        "config": bridge_dir / CONFIG_FILE_NAME,
        "command": bridge_dir / COMMAND_FILE_NAME,
        "inflight": bridge_dir / INFLIGHT_FILE_NAME,
        "response": bridge_dir / RESPONSE_FILE_NAME,
        "lock": bridge_dir / LOCK_FILE_NAME,
    }


def load_bridge_config():
    path = get_bridge_paths()["config"]

    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            return {}

        if data.get("host_name") != HOST_NAME:
            return {}

        token = data.get("token")

        if not isinstance(token, str) or len(token) < 32:
            return {}

        return data

    except (OSError, json.JSONDecodeError):
        return {}


def is_bridge_configured():
    return bool(load_bridge_config())


def _write_json_atomic(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = path.with_name(
        path.name + "." + uuid.uuid4().hex + ".tmp"
    )

    text = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    with open(temp_path, "x", encoding="utf-8", newline="\n") as file:
        file.write(text)
        file.flush()
        os.fsync(file.fileno())

    os.replace(temp_path, path)


def _read_json_limited(path, maximum_bytes=MAX_RESPONSE_BYTES):
    path = Path(path)

    try:
        size = path.stat().st_size

        if size <= 0 or size > maximum_bytes:
            return None

        raw = path.read_bytes()

        if len(raw) > maximum_bytes:
            return None

        data = json.loads(raw.decode("utf-8"))

        if isinstance(data, dict):
            return data

    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        pass

    return None


def _safe_unlink(path):
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        pass


def _acquire_lock(timeout_seconds):
    paths = get_bridge_paths()
    lock_path = paths["lock"]
    deadline = time.monotonic() + max(0.25, timeout_seconds)

    paths["dir"].mkdir(parents=True, exist_ok=True)

    while time.monotonic() < deadline:
        try:
            fd = os.open(
                lock_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o600,
            )

            try:
                os.write(
                    fd,
                    f"{os.getpid()}\n".encode("ascii", errors="ignore"),
                )
            finally:
                os.close(fd)

            return True

        except FileExistsError:
            try:
                age = time.time() - lock_path.stat().st_mtime

                if age > 30:
                    _safe_unlink(lock_path)
                    continue
            except OSError:
                pass

            time.sleep(0.05)

        except OSError:
            return False

    return False


def _release_lock():
    _safe_unlink(get_bridge_paths()["lock"])


def bridge_request(action, payload=None, timeout_seconds=DEFAULT_TIMEOUT_SECONDS):
    config = load_bridge_config()

    if not config:
        return (
            False,
            None,
            (
                "Le pont Edge AgentLocal n'est pas configuré. "
                "Exécute agent_tools\\edge_bridge\\setup_edge_bridge.py puis charge "
                "l'extension AgentLocal dans Edge."
            ),
        )

    if not isinstance(action, str) or not action.strip():
        return False, None, "Action de pont invalide."

    if payload is None:
        payload = {}

    if not isinstance(payload, dict):
        return False, None, "Paramètres de pont invalides."

    timeout_seconds = max(
        1.0,
        min(float(timeout_seconds), 15.0),
    )

    if not _acquire_lock(timeout_seconds):
        return (
            False,
            None,
            "Le pont Edge est déjà occupé par une autre commande.",
        )

    paths = get_bridge_paths()
    request_id = uuid.uuid4().hex
    token = config["token"]

    command = {
        "type": "command",
        "schema_version": 1,
        "request_id": request_id,
        "token": token,
        "action": action.strip(),
        "payload": payload,
        "created_at": time.time(),
    }

    try:
        _safe_unlink(paths["response"])
        _safe_unlink(paths["command"])
        _safe_unlink(paths["inflight"])

        _write_json_atomic(
            paths["command"],
            command,
        )

        deadline = time.monotonic() + timeout_seconds

        while time.monotonic() < deadline:
            response = _read_json_limited(
                paths["response"]
            )

            if response is not None:
                if response.get("type") != "result":
                    _safe_unlink(paths["response"])
                    time.sleep(0.05)
                    continue

                if response.get("request_id") != request_id:
                    _safe_unlink(paths["response"])
                    time.sleep(0.05)
                    continue

                if response.get("token") != token:
                    _safe_unlink(paths["response"])
                    return (
                        False,
                        None,
                        "Réponse du pont Edge non authentifiée.",
                    )

                _safe_unlink(paths["response"])

                success = bool(
                    response.get("ok", False)
                )

                message = response.get("message")

                if not isinstance(message, str):
                    message = "Réponse du pont Edge reçue."

                return (
                    success,
                    response,
                    message,
                )

            time.sleep(0.05)

        return (
            False,
            None,
            (
                "Le pont Edge n'a pas répondu. Vérifie que "
                "l'extension AgentLocal est chargée et que son "
                "hôte natif est enregistré."
            ),
        )

    finally:
        _safe_unlink(paths["command"])
        _safe_unlink(paths["inflight"])
        _release_lock()


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

    maximum_tabs = max(
        1,
        min(int(maximum_tabs), 10),
    )

    success, response, message = bridge_request(
        "close_site",
        {
            "url": url,
            "close_all": bool(close_all),
            "maximum_tabs": maximum_tabs,
            "allow_subdomains": bool(allow_subdomains),
        },
        timeout_seconds=timeout_seconds,
    )

    if not success:
        return False, 0, message

    count = response.get(
        "closed_count",
        0,
    ) if isinstance(response, dict) else 0

    try:
        count = int(count)
    except (TypeError, ValueError):
        count = 0

    count = max(0, min(count, 10))

    return True, count, message


def list_tabs_via_bridge(timeout_seconds=DEFAULT_TIMEOUT_SECONDS):
    success, response, message = bridge_request(
        "list_tabs",
        {},
        timeout_seconds=timeout_seconds,
    )

    if not success:
        return False, [], message

    tabs = response.get("tabs", [])

    if not isinstance(tabs, list):
        tabs = []

    safe_tabs = []

    for item in tabs[:50]:
        if not isinstance(item, dict):
            continue

        url = item.get("url")
        title = item.get("title")

        if not isinstance(url, str):
            continue

        safe_tabs.append(
            {
                "url": url[:MAX_URL_LENGTH],
                "title": title[:500] if isinstance(title, str) else "",
                "active": bool(item.get("active", False)),
            }
        )

    return True, safe_tabs, message


def generate_bridge_token():
    return secrets.token_hex(32)
