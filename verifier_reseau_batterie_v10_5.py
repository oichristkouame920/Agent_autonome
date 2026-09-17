from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app"))

import agent
from backends.deterministic_backend import interpret


def check(text, action, target):
    result = interpret(text)
    actions = result.get("actions", []) if isinstance(result, dict) else []
    ok = (
        result.get("understood") is True
        and len(actions) == 1
        and actions[0].get("action") == action
        and actions[0].get("target") == target
    )
    status = "OK" if ok else "ERREUR"
    print(f"{status} - {text} -> {action}/{target}")
    return ok


def main():
    permissions = json.loads((ROOT / "config" / "permissions.json").read_text(encoding="utf-8"))
    power = permissions.get("power_information_policy", {})
    network = permissions.get("network_information_policy", {})

    checks = [
        bool(power.get("enabled") and power.get("read_only")),
        bool(network.get("enabled") and network.get("read_only")),
        network.get("allow_external_speed_test") is False,
        network.get("allow_from_routine") is False,
        network.get("allow_from_habit") is False,
        check("il me reste combien de batterie ?", "read_power_info", "battery"),
        check("je suis branché au secteur ?", "read_power_info", "power"),
        check("mon réseau est actif ?", "read_network_info", "status"),
        check("quelle est mon IP locale ?", "read_network_info", "local_ip"),
        check("quelle est la vitesse de ma connexion ?", "read_network_info", "link_speed"),
        check("quel est le débit réseau actuel ?", "read_network_info", "traffic_speed"),
        check("fais un speedtest", "read_network_info", "internet_speed"),
    ]

    # Vérification du contrat, sans lecture réelle du réseau ni modification du système.
    checks.append(agent.validate_action({"schema_version": 1, "action": "read_network_info", "target": "link_speed"}) == (True, None))
    checks.append(agent.validate_action({"schema_version": 1, "action": "read_power_info", "target": "battery"}) == (True, None))

    if all(checks):
        print("\nV10.5 BATTERIE / RESEAU / VITESSE ACTIVE - verification non destructive OK")
        return 0
    print("\nERREUR - V10.5 incomplète ou incohérente")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
