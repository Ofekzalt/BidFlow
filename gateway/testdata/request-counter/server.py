from http.server import BaseHTTPRequestHandler, HTTPServer

state = {"n": 0, "fail_remaining": 2}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return

    def _send(self, code: int, body: bytes = b"") -> None:
        self.send_response(code)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path.startswith("/reset"):
            fail = 2
            if "fail=" in self.path:
                fail = int(self.path.split("fail=", 1)[1].split("&", 1)[0])
            state["n"] = 0
            state["fail_remaining"] = fail
            self._send(200, b"ok")
            return
        if self.path.startswith("/count"):
            self._send(200, str(state["n"]).encode())
            return
        state["n"] += 1
        if state["fail_remaining"] > 0:
            state["fail_remaining"] -= 1
            self._send(502)
            return
        self._send(200, b"ok")

    def do_POST(self) -> None:
        state["n"] += 1
        self._send(502)


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
