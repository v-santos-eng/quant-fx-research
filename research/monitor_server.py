"""Servidor local do monitor (somente 127.0.0.1). Serve o dashboard e endpoints que
leem os arquivos vivos escritos pelo ProgressReporter:

  GET /            -> docs/monitor.html
  GET /status      -> experiments/monitor/status.json
  GET /events?offset=N -> eventos novos desde a linha N (+ novo offset)

Uso:  python -m research.monitor_server [porta]   (padrão 8777)
"""
from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

MONITOR_DIR = Path("experiments/monitor")
HTML = Path("docs/monitor.html")


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body, ctype: str) -> None:
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        u = urlparse(self.path)
        if u.path in ("/", "/index.html"):
            body = HTML.read_text(encoding="utf-8") if HTML.exists() else "<h1>monitor.html ausente</h1>"
            self._send(200, body, "text/html; charset=utf-8")
        elif u.path == "/status":
            p = MONITOR_DIR / "status.json"
            self._send(200, p.read_text(encoding="utf-8") if p.exists() else "{}",
                       "application/json")
        elif u.path == "/events":
            offset = int(parse_qs(u.query).get("offset", ["0"])[0])
            p = MONITOR_DIR / "events.jsonl"
            # ponytail: relê o arquivo por poll; teto = logs enormes. Tail por seek se pesar.
            lines = p.read_text(encoding="utf-8").splitlines() if p.exists() else []
            new = [json.loads(x) for x in lines[offset:] if x.strip()]
            self._send(200, json.dumps({"offset": len(lines), "events": new}),
                       "application/json")
        else:
            self._send(404, "not found", "text/plain")

    def log_message(self, *args) -> None:  # silencia o log de acesso
        pass


def serve(port: int = 8777) -> None:
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"monitor em http://127.0.0.1:{port}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    serve(int(sys.argv[1]) if len(sys.argv) > 1 else 8777)
