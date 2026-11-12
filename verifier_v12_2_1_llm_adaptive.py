from pathlib import Path

from backends import llama_backend
from project_version import AGENTLOCAL_BUILD, AGENTLOCAL_VERSION

ROOT = Path(__file__).resolve().parent
assert AGENTLOCAL_VERSION == "12.5"
assert "llm-adaptive" in AGENTLOCAL_BUILD
assert callable(llama_backend.probe_llama_runtime)
assert callable(llama_backend.warm_server_status)
assert callable(llama_backend.stop_warm_server)
assert callable(llama_backend._strip_hidden_reasoning)
assert (ROOT / "upgrade_llm_config_v12_2_1.py").is_file()
source = (ROOT / "backends/llama_backend.py").read_text(encoding="utf-8")
for token in (
    "127.0.0.1",
    "llama-server.exe",
    "probe_slow_timeout_seconds",
    "warm_server_idle_seconds",
    "warm_server_min_available_ram_mb",
    "_strip_hidden_reasoning",
    "_run_llama_adaptive",
):
    assert token in source, token
assert "0.0.0.0" not in source
print("V12.2.1 LLM adaptatif local / retry / warm server / filtre raisonnement : OK")
