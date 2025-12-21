import os
from http.server import HTTPServer, BaseHTTPRequestHandler

# File path for shared volume
LOG_FILE = os.getenv("LOG_FILE", "/usr/src/app/files/log.txt")


class LogHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/status":
            try:
                with open(LOG_FILE, "r") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(content.encode())
            except FileNotFoundError:
                self.send_response(503)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Log file not ready yet")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    print(f"Log Reader server started in port {port}")
    server = HTTPServer(("0.0.0.0", port), LogHandler)
    server.serve_forever()

