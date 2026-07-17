from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from html import escape
from urllib.parse import parse_qs, urlparse

from .app import ReviewConsole
from .models import CONTROL_ACTIONS
from .store import StaleArtifactError


def handler_for(console: ReviewConsole) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _candidate_id(self) -> str:
            return urlparse(self.path).path.strip("/")

        def _send(self, status: HTTPStatus, body: str) -> None:
            encoded = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def do_GET(self) -> None:  # noqa: N802 - stdlib callback name
            try:
                self._send(HTTPStatus.OK, console.render(self._candidate_id()))
            except KeyError:
                self._send(HTTPStatus.NOT_FOUND, "<h1>Review item not found</h1>")

        def do_POST(self) -> None:  # noqa: N802 - stdlib callback name
            length = int(self.headers.get("Content-Length", "0"))
            form = parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True)
            one = lambda key: form.get(key, [""])[0]
            hashes = {key[5:]: values[0] for key, values in form.items() if key.startswith("hash:")}
            candidate_id, action = self._candidate_id(), one("action")
            try:
                if action in CONTROL_ACTIONS:
                    console.control(candidate_id, hashes, one("reviewer_id"), action, one("reason"))
                else:
                    console.decide(candidate_id, hashes, one("reviewer_id"), action,
                                   one("selected_rewrite_id") or None,
                                   one("edited_text") or None, one("reason"))
                self.send_response(HTTPStatus.SEE_OTHER)
                self.send_header("Location", f"/{candidate_id}")
                self.end_headers()
            except (KeyError, ValueError, PermissionError, StaleArtifactError) as error:
                self._send(HTTPStatus.CONFLICT,
                           f'<h1>Action blocked</h1><p role="alert">{escape(str(error))}</p>')

        def log_message(self, format: str, *args: object) -> None:
            return  # Avoid logging corpus data or form values.

    return Handler


def serve(console: ReviewConsole, host: str = "127.0.0.1", port: int = 8080) -> None:
    """Serve locally only by default; the caller owns lifecycle and fixture loading."""
    ThreadingHTTPServer((host, port), handler_for(console)).serve_forever()
