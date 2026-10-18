#!/usr/bin/env python3
"""A stand-in for an EC2 instance's metadata service (IMDSv2), for test/ only.

    test/fake-imds.py PORT_FILE [ok|token-refused|not-an-id]

BUILT FROM AWS'S DOCUMENTATION OF IMDSv2, NOT FROM A MEASUREMENT: a PUT to
/latest/api/token with a TTL header returns a token, and a GET carrying that token returns
the instance id. It exists for the cases a real instance cannot be made to produce on
demand; it is not the acceptance check -- docs/mdm/ec2.md's real-instance run is.

`token-refused` answers the token PUT with 403, a refusal the reporter must name; a metadata
service with its endpoint turned off is not reachable at all, which the test stages by
stopping the fake. `not-an-id` answers the id GET with something that is not one. A GET without the token is
refused with 401, so a reporter that dropped the header fails here rather than passing.

The port goes to PORT_FILE once the server is listening.
"""

import http.server
import pathlib
import sys

TOKEN = "fake-imds-token"
INSTANCE_ID = "i-0123456789abcdef0"

port_file = pathlib.Path(sys.argv[1])
mode = sys.argv[2] if len(sys.argv) > 2 else "ok"


class Handler(http.server.BaseHTTPRequestHandler):
    def answer(self, code: int, body: str) -> None:
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_PUT(self) -> None:
        if self.path != "/latest/api/token":
            return self.answer(404, "fake: not the token path")
        if not self.headers.get("X-aws-ec2-metadata-token-ttl-seconds"):
            return self.answer(400, "fake: missing token TTL header")
        if mode == "token-refused":
            return self.answer(403, "Forbidden")
        return self.answer(200, TOKEN)

    def do_GET(self) -> None:
        if self.path != "/latest/meta-data/instance-id":
            return self.answer(404, "fake: not the instance-id path")
        if self.headers.get("X-aws-ec2-metadata-token") != TOKEN:
            return self.answer(401, "Unauthorized")
        if mode == "not-an-id":
            return self.answer(200, "<html>captive portal</html>")
        return self.answer(200, INSTANCE_ID)

    def log_message(self, *args: object) -> None:
        pass


server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
port_file.write_text(str(server.server_address[1]))
server.serve_forever()
