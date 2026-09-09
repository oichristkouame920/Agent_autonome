import json
import os
import secrets
import socket
import sys

from pathlib import Path


EXTENSION_ID = "odhigmilcgpndpjgjkbfmpoiiblklcgf"

ROOT_DIR = Path(__file__).resolve().parents[2]

CONFIG_FILE = (
    ROOT_DIR
    / "config"
    / "browser_bridge.json"
)

EXTENSION_DIR = (
    ROOT_DIR
    / "browser_extension"
)

EXTENSION_CONFIG_FILE = (
    EXTENSION_DIR
    / "bridge_config.js"
)

EXTENSION_MANIFEST = (
    EXTENSION_DIR
    / "manifest.json"
)

OLD_NATIVE_REGISTRY_PATH = (
    r"Software\Microsoft\Edge\NativeMessagingHosts\com.agentlocal.bridge"
)


def find_available_port(
    host="127.0.0.1",
    start_port=8765,
    end_port=8795,
):
    for port in range(
        start_port,
        end_port + 1,
    ):
        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM,
        )

        try:
            sock.setsockopt(
                socket.SOL_SOCKET,
                socket.SO_EXCLUSIVEADDRUSE,
                1,
            )
        except (OSError, AttributeError):
            pass

        try:
            sock.bind(
                (
                    host,
                    port,
                )
            )
            return port
        except OSError:
            pass
        finally:
            sock.close()

    return None


def validate_extension_manifest():
    try:
        with open(
            EXTENSION_MANIFEST,
            "r",
            encoding="utf-8",
        ) as file:
            manifest = json.load(
                file
            )
    except (
        OSError,
        json.JSONDecodeError,
    ) as error:
        raise RuntimeError(
            f"Manifest Edge invalide : {error}"
        ) from error

    if manifest.get(
        "manifest_version"
    ) != 3:
        raise RuntimeError(
            "L'extension doit utiliser Manifest V3."
        )

    permissions = manifest.get(
        "permissions",
        [],
    )

    if "nativeMessaging" in permissions:
        raise RuntimeError(
            "L'ancien droit Native Messaging est encore présent."
        )

    host_permissions = manifest.get(
        "host_permissions",
        [],
    )

    if "http://127.0.0.1/*" not in host_permissions:
        raise RuntimeError(
            "L'extension n'autorise pas le pont local 127.0.0.1."
        )


def write_json_atomic(
    path,
    payload,
):
    path = Path(
        path
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp = path.with_suffix(
        path.suffix + ".tmp"
    )

    with open(
        temp,
        "w",
        encoding="utf-8",
        newline="\n",
    ) as file:
        json.dump(
            payload,
            file,
            ensure_ascii=False,
            indent=2,
        )
        file.write("\n")
        file.flush()
        os.fsync(
            file.fileno()
        )

    os.replace(
        temp,
        path,
    )


def write_extension_config(
    config
):
    payload = {
        "schemaVersion": 1,
        "enabled": True,
        "host": config["host"],
        "port": config["port"],
        "extensionId": config["extension_id"],
        "token": config["token"],
        "pollIntervalMs": config["poll_interval_ms"],
    }

    text = (
        "globalThis.AGENTLOCAL_BRIDGE_CONFIG = "
        "Object.freeze("
        + json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        + ");\n"
    )

    EXTENSION_CONFIG_FILE.write_text(
        text,
        encoding="utf-8",
    )


def remove_old_native_registration():
    if os.name != "nt":
        return False

    try:
        import winreg

        winreg.DeleteKey(
            winreg.HKEY_CURRENT_USER,
            OLD_NATIVE_REGISTRY_PATH,
        )

        return True

    except FileNotFoundError:
        return False

    except (
        PermissionError,
        OSError,
    ):
        return False


def remove_old_local_bridge_files():
    local_appdata = os.environ.get(
        "LOCALAPPDATA"
    )

    if not local_appdata:
        return

    bridge_dir = (
        Path(
            local_appdata
        )
        / "AgentLocalBridge"
    )

    if not bridge_dir.is_dir():
        return

    allowed_names = {
        "bridge_config.json",
        "command.json",
        "command.inflight.json",
        "response.json",
        "agent.lock",
    }

    try:
        children = list(
            bridge_dir.iterdir()
        )
    except OSError:
        return

    if any(
        child.name not in allowed_names
        for child in children
    ):
        return

    for child in children:
        try:
            if child.is_file():
                child.unlink(
                    missing_ok=True
                )
        except OSError:
            pass

    try:
        bridge_dir.rmdir()
    except OSError:
        pass


def main():
    print()
    print("=" * 68)
    print("CONFIGURATION DU PONT EDGE HTTP LOCAL - AGENTLOCAL")
    print("=" * 68)
    print()

    if os.name != "nt":
        print(
            "ERREUR : cette configuration doit être exécutée sous Windows."
        )
        return 1

    try:
        validate_extension_manifest()
    except RuntimeError as error:
        print(
            f"ERREUR : {error}"
        )
        return 1

    port = find_available_port()

    if port is None:
        print(
            "ERREUR : aucun port local libre entre 8765 et 8795."
        )
        return 1

    token = secrets.token_hex(
        32
    )

    config = {
        "schema_version": 1,
        "enabled": True,
        "host": "127.0.0.1",
        "port": port,
        "extension_id": EXTENSION_ID,
        "token": token,
        "poll_interval_ms": 500,
        "request_timeout_seconds": 12,
        "maximum_body_bytes": 262144,
    }

    write_json_atomic(
        CONFIG_FILE,
        config,
    )

    try:
        write_extension_config(
            config
        )
    except OSError as error:
        print(
            f"ERREUR : impossible d'écrire bridge_config.js : {error}"
        )
        return 1

    old_registry_removed = (
        remove_old_native_registration()
    )

    remove_old_local_bridge_files()

    print(
        "Configuration locale créée :"
    )
    print(
        f"- {CONFIG_FILE}"
    )
    print(
        f"- {EXTENSION_CONFIG_FILE}"
    )
    print()
    print(
        f"Pont : http://127.0.0.1:{port}"
    )
    print(
        f"ID extension attendu : {EXTENSION_ID}"
    )
    print()

    if old_registry_removed:
        print(
            "Ancien enregistrement Native Messaging HKCU supprimé."
        )

    print()
    print(
        "IMPORTANT : bridge_config.js contient un secret local et "
        "est ignoré par Git."
    )
    print()
    print(
        "Dans Edge :"
    )
    print(
        "1. Ouvre edge://extensions/"
    )
    print(
        "2. Active le Mode développeur."
    )
    print(
        "3. Charge ou RECHARGE l'extension AgentLocal Browser Bridge."
    )
    print(
        f"4. Dossier : {EXTENSION_DIR}"
    )
    print(
        f"5. Vérifie l'ID : {EXTENSION_ID}"
    )
    print()
    print(
        "Ensuite teste avec :"
    )
    print(
        r"  .\.venv\Scripts\python.exe .\agent_tools\edge_bridge\test_edge_bridge.py"
    )
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
