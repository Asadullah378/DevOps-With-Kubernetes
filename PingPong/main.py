import os
from http.server import HTTPServer, BaseHTTPRequestHandler

# File path for persistent volume
COUNTER_FILE = os.getenv("COUNTER_FILE", "/usr/src/app/data/counter.txt")


def read_counter():
    """Read counter from file"""
    try:
        with open(COUNTER_FILE, "r") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0


def write_counter(count):
    """Write counter to file"""
    with open(COUNTER_FILE, "w") as f:
        f.write(str(count))


class PingPongHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/pingpong":
            counter = read_counter()
            response = f"pong {counter}"
            write_counter(counter + 1)
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(response.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    print(f"Server started in port {port}")
    server = HTTPServer(("0.0.0.0", port), PingPongHandler)
    server.serve_forever()
