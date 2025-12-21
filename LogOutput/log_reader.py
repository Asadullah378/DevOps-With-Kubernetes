import os
from http.server import HTTPServer, BaseHTTPRequestHandler

# File paths for shared volumes
LOG_FILE = os.getenv("LOG_FILE", "/usr/src/app/files/log.txt")
COUNTER_FILE = os.getenv("COUNTER_FILE", "/usr/src/app/data/counter.txt")


def read_pingpong_count():
    """Read ping-pong counter from persistent volume"""
    try:
        with open(COUNTER_FILE, "r") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0


class LogHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/status":
            try:
                with open(LOG_FILE, "r") as f:
                    # read last line
                    log_content = f.readlines()[-1].strip()
                
                pingpong_count = read_pingpong_count()
                
                # Format: timestamp: random_string.\nPing / Pongs: N
                response = f"{log_content}\nPing / Pongs: {pingpong_count}"
                
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(response.encode())
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
