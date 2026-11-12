from pathlib import Path

ROOT = Path(__file__).resolve().parent

ico = ROOT / "assets" / "agentlocal.ico"
png = ROOT / "assets" / "agentlocal_icon.png"
start_vbs = ROOT / "runtime" / "start_agentlocal_gui.vbs"
shortcut_vbs = ROOT / "runtime" / "create_agentlocal_shortcuts.vbs"
launcher = ROOT / "AgentLocal.bat"
gui = ROOT / "app" / "gui.py"

assert ico.is_file(), "Icône ICO AgentLocal manquante"
assert png.is_file(), "Icône PNG AgentLocal manquante"
assert ico.read_bytes()[:4] == b"\x00\x00\x01\x00", "Format ICO invalide"
assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n", "Format PNG invalide"

for path in (start_vbs, shortcut_vbs):
    data = path.read_bytes()
    assert data and not data.startswith(b"\xef\xbb\xbf"), f"BOM UTF-8 interdit : {path.name}"
    data.decode("ascii")

text = gui.read_text(encoding="utf-8")
for needle in ("APP_ICON_ICO", "APP_ICON_PNG", "_apply_window_icon", "_show_startup_splash", "SetCurrentProcessExplicitAppUserModelID"):
    assert needle in text, f"Branding GUI absent : {needle}"

bat = launcher.read_text(encoding="utf-8-sig", errors="replace").lower()
assert "creer / reparer le raccourci agentlocal" in bat
assert ":shortcut" in bat
assert "create_agentlocal_shortcuts.vbs" in bat

shortcut_text = shortcut_vbs.read_text(encoding="ascii")
assert "AgentLocal.lnk" in shortcut_text
assert "agentlocal.ico" in shortcut_text
assert 'TargetPath = "wscript.exe"' in shortcut_text

print("V12.5.1 branding / icône / lanceur rapide : OK")
