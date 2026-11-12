from __future__ import annotations
import json
from pathlib import Path
from project_version import AGENTLOCAL_BUILD, AGENTLOCAL_VERSION
ROOT=Path(__file__).resolve().parent
assert AGENTLOCAL_VERSION == "12.5"
assert "v12.2.2-windows-autostart" in AGENTLOCAL_BUILD
for rel in (
    "app/windows_startup.py",
    "app/single_instance.py",
    "configure_windows_startup_v12_2_2.py",
    "upgrade_automation_config_v12_2_2.py",
):
    assert (ROOT/rel).is_file(), rel
cfg=json.loads((ROOT/'config/automation.json').read_text(encoding='utf-8'))
assert cfg['morning_automation']['trigger']=='first_unlock_seen'
assert cfg['windows_startup']['single_instance'] is True
launcher=(ROOT/'AgentLocal.bat').read_text(encoding='utf-8-sig')
assert 'goto AUTOSTART' in launcher and '--background' in launcher
source=(ROOT/'app/windows_startup.py').read_text(encoding='utf-8')
assert 'HKEY_CURRENT_USER' in source and 'HKEY_LOCAL_MACHINE' not in source
print('V12.2.2 démarrage Windows / arrière-plan / instance unique : OK')
