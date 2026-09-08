import sys

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
APP_DIR = ROOT_DIR / "app"

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from browser_bridge import bridge_request, list_tabs_via_bridge


def main():
    print()
    print("=" * 68)
    print("TEST PONT EDGE AGENTLOCAL")
    print("=" * 68)
    print()

    success, _, message = bridge_request(
        "ping",
        {},
        timeout_seconds=5.0,
    )

    print("Ping :", "OK" if success else "ECHEC")
    print(message)
    print()

    if not success:
        return 1

    success, tabs, message = list_tabs_via_bridge(
        timeout_seconds=5.0
    )

    print("Lecture des onglets :", "OK" if success else "ECHEC")
    print(message)

    if success:
        for index, tab in enumerate(tabs[:20], start=1):
            marker = "*" if tab.get("active") else "-"
            print(
                f"{marker} {index}. {tab.get('title', '')} | "
                f"{tab.get('url', '')}"
            )

    print()
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
