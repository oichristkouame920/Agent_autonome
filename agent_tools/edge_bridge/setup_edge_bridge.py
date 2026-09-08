import argparse
import json
import os
import secrets
import subprocess
import sys
import time

from pathlib import Path


HOST_NAME = "com.agentlocal.bridge"
EXTENSION_ID = "odhigmilcgpndpjgjkbfmpoiiblklcgf"
REGISTRY_PATH = (
    "Software\\Microsoft\\Edge\\NativeMessagingHosts\\"
    + HOST_NAME
)

ROOT_DIR = Path(__file__).resolve().parents[2]
HOST_DIR = ROOT_DIR / "browser_native_host"
HOST_SOURCE = HOST_DIR / "agentlocal_native_host.c"
HOST_EXE = HOST_DIR / "agentlocal_native_host.exe"
HOST_MANIFEST = HOST_DIR / "com.agentlocal.bridge.json"
EXTENSION_DIR = ROOT_DIR / "browser_extension"
EXTENSION_MANIFEST = EXTENSION_DIR / "manifest.json"


def get_bridge_dir():
    local_appdata = os.environ.get("LOCALAPPDATA")

    if local_appdata:
        base = Path(local_appdata)
    else:
        base = Path.home() / "AppData" / "Local"

    return base / "AgentLocalBridge"


def find_vswhere():
    candidates = []

    program_files_x86 = os.environ.get("ProgramFiles(x86)")
    program_files = os.environ.get("ProgramFiles")

    if program_files_x86:
        candidates.append(
            Path(program_files_x86)
            / "Microsoft Visual Studio"
            / "Installer"
            / "vswhere.exe"
        )

    if program_files:
        candidates.append(
            Path(program_files)
            / "Microsoft Visual Studio"
            / "Installer"
            / "vswhere.exe"
        )

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    return None


def find_visual_studio_installation():
    vswhere = find_vswhere()

    if vswhere is None:
        return None

    command = [
        str(vswhere),
        "-latest",
        "-products",
        "*",
        "-requires",
        "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
        "-property",
        "installationPath",
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            shell=False,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    if result.returncode != 0:
        return None

    value = result.stdout.strip()

    if not value:
        return None

    path = Path(value)

    if not path.exists():
        return None

    return path


def compile_native_host():
    if os.name != "nt":
        raise RuntimeError(
            "La compilation du pont natif doit être exécutée sous Windows."
        )

    installation = find_visual_studio_installation()

    if installation is None:
        raise RuntimeError(
            "Visual Studio Build Tools avec les outils C++ n'a pas été trouvé."
        )

    vcvars = (
        installation
        / "VC"
        / "Auxiliary"
        / "Build"
        / "vcvars64.bat"
    )

    if not vcvars.is_file():
        raise RuntimeError(
            "vcvars64.bat est introuvable dans Visual Studio Build Tools."
        )

    if not HOST_SOURCE.is_file():
        raise RuntimeError(
            f"Source native introuvable : {HOST_SOURCE}"
        )

    HOST_DIR.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------
    # IMPORTANT : ne pas transmettre directement la commande
    # contenant vcvars64.bat à cmd.exe via /c. Sous Windows,
    # l'encodage des guillemets de subprocess peut transformer
    # les guillemets en \"...\" et cmd.exe les interprète
    # alors comme des caractères littéraux.
    #
    # On génère donc un petit fichier .cmd temporaire avec des
    # guillemets Windows normaux, puis on exécute ce fichier.
    # --------------------------------------------------------

    build_script = HOST_DIR / "_build_agentlocal_native_host.cmd"

    script_content = (
        "@echo off\r\n"
        "setlocal\r\n"
        f'call "{vcvars}" >nul\r\n'
        "if errorlevel 1 exit /b %errorlevel%\r\n"
        f'cl /nologo /O2 /W4 /DUNICODE /D_UNICODE "{HOST_SOURCE}" /Fe:"{HOST_EXE}"\r\n'
        "set BUILD_RESULT=%errorlevel%\r\n"
        "endlocal & exit /b %BUILD_RESULT%\r\n"
    )

    try:
        build_script.write_text(
            script_content,
            encoding="utf-8",
            newline="",
        )
    except OSError as error:
        raise RuntimeError(
            f"Impossible de créer le script temporaire de compilation : {error}"
        ) from error

    comspec = os.environ.get(
        "COMSPEC",
        r"C:\Windows\System32\cmd.exe",
    )

    try:
        result = subprocess.run(
            [
                comspec,
                "/d",
                "/c",
                str(build_script),
            ],
            cwd=str(HOST_DIR),
            capture_output=True,
            text=True,
            check=False,
            shell=False,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise RuntimeError(
            f"Impossible de lancer la compilation du pont natif : {error}"
        ) from error
    finally:
        try:
            build_script.unlink(missing_ok=True)
        except OSError:
            pass

    if result.returncode != 0 or not HOST_EXE.is_file():
        details = "\n".join(
            value
            for value in [
                result.stdout.strip(),
                result.stderr.strip(),
            ]
            if value
        )

        raise RuntimeError(
            "La compilation du pont natif a échoué."
            + (f"\n{details}" if details else "")
        )

    return HOST_EXE


def validate_manifests():
    for path in [HOST_MANIFEST, EXTENSION_MANIFEST]:
        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError(
                f"Manifest invalide : {path} ({error})"
            ) from error

        if not isinstance(data, dict):
            raise RuntimeError(
                f"Manifest invalide : {path}"
            )

    with open(HOST_MANIFEST, "r", encoding="utf-8") as file:
        host_manifest = json.load(file)

    expected_origin = f"chrome-extension://{EXTENSION_ID}/"

    if host_manifest.get("name") != HOST_NAME:
        raise RuntimeError("Nom d'hôte natif incorrect.")

    if expected_origin not in host_manifest.get("allowed_origins", []):
        raise RuntimeError(
            "L'ID de l'extension n'est pas autorisé dans le manifest natif."
        )


def register_native_host():
    import winreg

    manifest_path = str(HOST_MANIFEST.resolve())

    with winreg.CreateKeyEx(
        winreg.HKEY_CURRENT_USER,
        REGISTRY_PATH,
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        winreg.SetValueEx(
            key,
            None,
            0,
            winreg.REG_SZ,
            manifest_path,
        )

    return manifest_path


def create_bridge_config():
    bridge_dir = get_bridge_dir()
    bridge_dir.mkdir(parents=True, exist_ok=True)

    config_file = bridge_dir / "bridge_config.json"
    token = None

    if config_file.is_file():
        try:
            with open(config_file, "r", encoding="utf-8") as file:
                existing = json.load(file)

            if isinstance(existing, dict):
                existing_token = existing.get("token")

                if (
                    isinstance(existing_token, str)
                    and len(existing_token) >= 32
                ):
                    token = existing_token
        except (OSError, json.JSONDecodeError):
            pass

    if token is None:
        token = secrets.token_hex(32)

    payload = {
        "schema_version": 1,
        "host_name": HOST_NAME,
        "extension_id": EXTENSION_ID,
        "token": token,
        "project_root": str(ROOT_DIR.resolve()),
        "installed_at": time.time(),
    }

    temp = config_file.with_suffix(".tmp")

    with open(temp, "w", encoding="utf-8", newline="\n") as file:
        json.dump(
            payload,
            file,
            ensure_ascii=False,
            indent=2,
        )
        file.write("\n")
        file.flush()
        os.fsync(file.fileno())

    os.replace(temp, config_file)

    for name in [
        "command.json",
        "command.inflight.json",
        "response.json",
        "agent.lock",
    ]:
        try:
            (bridge_dir / name).unlink(missing_ok=True)
        except OSError:
            pass

    return config_file


def _read_policy_list(winreg, root, path):
    values = []

    try:
        with winreg.OpenKey(
            root,
            path,
            0,
            winreg.KEY_READ,
        ) as key:
            index = 0

            while True:
                try:
                    _, value, _ = winreg.EnumValue(
                        key,
                        index,
                    )
                except OSError:
                    break

                if isinstance(value, str):
                    values.append(value.strip())

                index += 1

    except (FileNotFoundError, PermissionError, OSError):
        pass

    return values


def check_edge_native_messaging_policy():
    if os.name != "nt":
        return []

    warnings = []

    try:
        import winreg

        policy_base = r"Software\Policies\Microsoft\Edge"

        for root, root_name in [
            (winreg.HKEY_CURRENT_USER, "HKCU"),
            (winreg.HKEY_LOCAL_MACHINE, "HKLM"),
        ]:
            try:
                with winreg.OpenKey(
                    root,
                    policy_base,
                    0,
                    winreg.KEY_READ,
                ) as key:
                    try:
                        value, _ = winreg.QueryValueEx(
                            key,
                            "NativeMessagingUserLevelHosts",
                        )

                        if int(value) == 0:
                            warnings.append(
                                f"{root_name} : NativeMessagingUserLevelHosts "
                                "désactive les hôtes natifs installés au niveau utilisateur."
                            )
                    except (FileNotFoundError, TypeError, ValueError):
                        pass
            except (FileNotFoundError, PermissionError, OSError):
                pass

            blocklist = _read_policy_list(
                winreg,
                root,
                policy_base + r"\NativeMessagingBlocklist",
            )

            allowlist = _read_policy_list(
                winreg,
                root,
                policy_base + r"\NativeMessagingAllowlist",
            )

            if HOST_NAME in blocklist:
                warnings.append(
                    f"{root_name} : {HOST_NAME} est explicitement bloqué "
                    "par NativeMessagingBlocklist."
                )

            if "*" in blocklist and HOST_NAME not in allowlist:
                warnings.append(
                    f"{root_name} : tous les hôtes Native Messaging sont bloqués "
                    f"et {HOST_NAME} n'est pas dans NativeMessagingAllowlist."
                )

    except ImportError:
        pass

    return warnings


def print_next_steps(config_file, manifest_path):
    print()
    print("=" * 68)
    print("PONT EDGE AGENTLOCAL - INSTALLATION TERMINEE")
    print("=" * 68)
    print()
    print(f"Hôte natif : {HOST_EXE}")
    print(f"Manifest natif : {manifest_path}")
    print(f"Configuration locale : {config_file}")
    print(f"ID attendu de l'extension : {EXTENSION_ID}")
    print()
    print("Étape Edge à faire une seule fois :")
    print("1. Ouvre edge://extensions/")
    print("2. Active 'Mode développeur'.")
    print("3. Clique sur 'Charger l'extension décompressée'.")
    print(f"4. Sélectionne : {EXTENSION_DIR}")
    print(f"5. Vérifie que l'ID affiché est : {EXTENSION_ID}")
    print()
    print("Ensuite ferme et relance AgentLocal, puis teste :")
    print("  ferme le site YouTube")
    print()


def uninstall_native_host():
    if os.name != "nt":
        raise RuntimeError("Désinstallation disponible uniquement sous Windows.")

    import winreg

    try:
        winreg.DeleteKey(
            winreg.HKEY_CURRENT_USER,
            REGISTRY_PATH,
        )
    except FileNotFoundError:
        pass

    print("Enregistrement du pont Edge supprimé pour l'utilisateur courant.")


def main():
    parser = argparse.ArgumentParser(
        description="Installe le pont local Microsoft Edge pour AgentLocal."
    )

    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Retire uniquement l'enregistrement Native Messaging HKCU.",
    )

    args = parser.parse_args()

    if args.uninstall:
        uninstall_native_host()
        return 0

    if os.name != "nt":
        print("ERREUR : ce script doit être exécuté sous Windows.")
        return 1

    try:
        validate_manifests()
        compile_native_host()
        manifest_path = register_native_host()
        config_file = create_bridge_config()
    except RuntimeError as error:
        print(f"ERREUR : {error}")
        return 1

    warnings = check_edge_native_messaging_policy()

    print_next_steps(
        config_file,
        manifest_path,
    )

    for warning in warnings:
        print(f"ATTENTION : {warning}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
