#!/usr/bin/env python3
"""A stand-in for a Compute Engine VM's guest-attributes endpoint, for test/ only.

    test/fake-metadata-server.py STORE_DIR PORT_FILE [ok|disabled]

BUILT FROM MEASUREMENTS, NOT FROM DOCUMENTATION. Each answer below is what a real Debian 12
VM's metadata server returned on 2026-10-03: a value over 262,144 bytes refused with HTTP 400
and that message, and HTTP 403 with that message once enable-guest-attributes=FALSE. It exists
for the cases a real VM cannot be made to produce on demand; it is not the acceptance check --
docs/mdm/gce.md's real-VM run is.

One answer is the fake's own and says so: a PUT without `Metadata-Flavor: Google` is refused
with 400, so a reporter that dropped the header fails here rather than passing.

A PUT stores its body under STORE_DIR/<namespace>/<key>, byte for byte. The port goes to
PORT_FILE once the server is listening.
"""

import http.server
import pathlib
import sys

PREFIX = "/computeMetadata/v1/instance/guest-attributes/"
CAP = 262144

store = pathlib.Path(sys.argv[1])
port_file = pathlib.Path(sys.argv[2])
mode = sys.argv[3] if len(sys.argv) > 3 else "ok"


class Handler(http.server.BaseHTTPRequestHandler):
    def answer(self, code, body):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_PUT(self):
        value = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        if (
            not self.path.startswith(PREFIX)
            or self.path.count("/") != PREFIX.count("/") + 1
        ):
            return self.answer(404, "fake: not a guest attribute path")
        if self.headers.get("Metadata-Flavor") != "Google":
            return self.answer(400, "fake: missing Metadata-Flavor: Google")
        if mode == "disabled":
            return self.answer(403, "Guest attributes endpoint access is disabled.")
        if len(value) > CAP:
            return self.answer(
                400,
                f"Maximum value of {CAP} bytes allowed ({len(value)}found )",
            )
        namespace, key = self.path[len(PREFIX) :].split("/")
        (store / namespace).mkdir(parents=True, exist_ok=True)
        (store / namespace / key).write_bytes(value)
        return self.answer(200, "")

    def log_message(self, *args):
        pass


server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
port_file.write_text(str(server.server_address[1]))
server.serve_forever()
