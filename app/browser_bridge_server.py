import hmac
import json
import threading
import time

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


MAX_BODY_BYTES_HARD = 256 * 1024


class BridgeState:
    def __init__(self):
        self._condition = threading.Condition()
        self._pending = None
        self._claimed = False
        self._result = None

    def submit_and_wait(self, command, timeout_seconds):
        request_id = command.get("request_id")

        if not isinstance(request_id, str) or not request_id:
            return False, None, "Identifiant de requête invalide."

        deadline = time.monotonic() + timeout_seconds

        with self._condition:
            while self._pending is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False, None, "Le pont Edge est déjà occupé."
                self._condition.wait(min(remaining, 0.1))

            self._pending = dict(command)
            self._claimed = False
            self._result = None
            self._condition.notify_all()

            while True:
                if (
                    isinstance(self._result, dict)
                    and self._result.get("request_id") == request_id
                ):
                    result = self._result
                    self._result = None
                    self._pending = None
                    self._claimed = False
                    self._condition.notify_all()
                    return True, result, None

                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    if (
                        isinstance(self._pending, dict)
                        and self._pending.get("request_id") == request_id
                    ):
                        self._pending = None
                        self._claimed = False
                        self._result = None
                        self._condition.notify_all()

                    return (
                        False,
                        None,
                        (
                            "Le pont Edge local n'a pas répondu dans le délai prévu. "
                            "Vérifie que l'extension AgentLocal est chargée puis recharge-la "
                            "dans edge://extensions/."
                        ),
                    )

                self._condition.wait(min(remaining, 0.1))

    def claim_command(self):
        with self._condition:
            if self._pending is None or self._claimed:
                return None

            self._claimed = True
            return dict(self._pending)

    def complete(self, result):
        if not isinstance(result, dict):
            return False

        request_id = result.get("request_id")

        with self._condition:
            if not isinstance(self._pending, dict):
                return False

            if self._pending.get("request_id") != request_id:
                return False

            expected_action = self._pending.get("action")
            result_action = result.get("action")

            if result_action != expected_action:
                return False

            self._result = dict(result)
            self._condition.notify_all()
            return True

    def release_claim_if_needed(self, request_id):
        with self._condition:
            if (
                isinstance(self._pending, dict)
                and self._pending.get("request_id") == request_id
                and self._result is None
            ):
                self._claimed = False
                self._condition.notify_all()


class AgentLocalHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, server_address, handler_class, bridge_config, bridge_state):
        super().__init__(server_address, handler_class)
        self.bridge_config = bridge_config
        self.bridge_state = bridge_state


class BridgeRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "AgentLocalBridge/2.0"

    def log_message(self, format, *args):
        return

    def _origin(self):
        return self.headers.get("Origin", "").strip()

    def _expected_origin(self):
        extension_id = self.server.bridge_config["extension_id"]
        return f"chrome-extension://{extension_id}"

    def _cors_allowed(self):
        origin = self._origin()
        return (not origin) or hmac.compare_digest(
            origin,
            self._expected_origin(),
        )

    def _authenticated(self):
        if not self._cors_allowed():
            return False

        config = self.server.bridge_config

        token = self.headers.get(
            "X-AgentLocal-Token",
            "",
        )

        extension_id = self.headers.get(
            "X-AgentLocal-Extension-ID",
            "",
        )

        return (
            isinstance(token, str)
            and isinstance(extension_id, str)
            and hmac.compare_digest(
                token,
                config["token"],
            )
            and hmac.compare_digest(
                extension_id,
                config["extension_id"],
            )
        )

    def _common_headers(self):
        self.send_header(
            "Cache-Control",
            "no-store",
        )
        self.send_header(
            "X-Content-Type-Options",
            "nosniff",
        )

        origin = self._origin()

        if origin and hmac.compare_digest(
            origin,
            self._expected_origin(),
        ):
            self.send_header(
                "Access-Control-Allow-Origin",
                origin,
            )
            self.send_header(
                "Vary",
                "Origin",
            )

    def _send_empty(self, status):
        self.send_response(status)
        self._common_headers()
        self.send_header(
            "Content-Length",
            "0",
        )
        self.end_headers()

    def _send_json(self, status, payload):
        raw = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

        self.send_response(status)
        self._common_headers()
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )
        self.send_header(
            "Content-Length",
            str(len(raw)),
        )
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self):
        if not self._cors_allowed():
            self._send_empty(403)
            return

        self.send_response(204)
        self._common_headers()
        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, OPTIONS",
        )
        self.send_header(
            "Access-Control-Allow-Headers",
            (
                "Content-Type, "
                "X-AgentLocal-Token, "
                "X-AgentLocal-Extension-ID"
            ),
        )
        self.send_header(
            "Access-Control-Max-Age",
            "600",
        )
        self.send_header(
            "Content-Length",
            "0",
        )
        self.end_headers()

    def do_GET(self):
        if self.path != "/v1/command":
            self._send_empty(404)
            return

        if not self._authenticated():
            self._send_empty(403)
            return

        command = self.server.bridge_state.claim_command()

        if command is None:
            self._send_empty(204)
            return

        request_id = command.get("request_id", "")

        try:
            self._send_json(
                200,
                command,
            )
        except (BrokenPipeError, ConnectionResetError, OSError):
            self.server.bridge_state.release_claim_if_needed(
                request_id
            )

    def do_POST(self):
        if self.path != "/v1/result":
            self._send_empty(404)
            return

        if not self._authenticated():
            self._send_empty(403)
            return

        length_value = self.headers.get(
            "Content-Length",
            "",
        )

        try:
            length = int(length_value)
        except (TypeError, ValueError):
            self._send_empty(411)
            return

        maximum = min(
            int(
                self.server.bridge_config.get(
                    "maximum_body_bytes",
                    MAX_BODY_BYTES_HARD,
                )
            ),
            MAX_BODY_BYTES_HARD,
        )

        if length <= 0 or length > maximum:
            self._send_empty(413)
            return

        try:
            raw = self.rfile.read(length)
            payload = json.loads(
                raw.decode("utf-8")
            )
        except (
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            self._send_empty(400)
            return

        if not isinstance(payload, dict):
            self._send_empty(400)
            return

        if payload.get("type") != "result":
            self._send_empty(400)
            return

        if not self.server.bridge_state.complete(
            payload
        ):
            self._send_empty(409)
            return

        self._send_json(
            200,
            {
                "ok": True,
            },
        )


_STATE = BridgeState()
_SERVER = None
_SERVER_THREAD = None
_SERVER_LOCK = threading.Lock()


def ensure_server_started(config):
    global _SERVER
    global _SERVER_THREAD

    if not isinstance(config, dict):
        return False, "Configuration du pont invalide."

    with _SERVER_LOCK:
        if (
            _SERVER is not None
            and _SERVER_THREAD is not None
            and _SERVER_THREAD.is_alive()
        ):
            return True, None

        host = config.get(
            "host",
            "127.0.0.1",
        )

        port = config.get(
            "port",
            8765,
        )

        if host != "127.0.0.1":
            return (
                False,
                "Le pont Edge doit écouter uniquement sur 127.0.0.1.",
            )

        try:
            port = int(port)
        except (TypeError, ValueError):
            return False, "Port du pont Edge invalide."

        if not (1024 <= port <= 65535):
            return False, "Port du pont Edge invalide."

        try:
            server = AgentLocalHTTPServer(
                (host, port),
                BridgeRequestHandler,
                config,
                _STATE,
            )
        except OSError as error:
            return (
                False,
                (
                    f"Impossible de démarrer le pont Edge local sur "
                    f"{host}:{port} : {error}"
                ),
            )

        thread = threading.Thread(
            target=server.serve_forever,
            name="AgentLocalEdgeBridge",
            daemon=True,
        )

        thread.start()

        _SERVER = server
        _SERVER_THREAD = thread

        return True, None


def submit_command(command, timeout_seconds):
    return _STATE.submit_and_wait(
        command,
        timeout_seconds,
    )


def stop_server():
    global _SERVER
    global _SERVER_THREAD

    with _SERVER_LOCK:
        server = _SERVER
        thread = _SERVER_THREAD

        _SERVER = None
        _SERVER_THREAD = None

    if server is not None:
        try:
            server.shutdown()
        except OSError:
            pass

        try:
            server.server_close()
        except OSError:
            pass

    if thread is not None and thread.is_alive():
        thread.join(timeout=1.0)
