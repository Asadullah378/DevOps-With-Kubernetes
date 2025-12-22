import os
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler

# File path for shared volume (between log-writer and log-reader)
LOG_FILE = os.getenv("LOG_FILE", "/usr/src/app/files/log.txt")

# PingPong service URL
PINGPONG_URL = os.getenv("PINGPONG_URL", "http://pingpong-svc:2346/pings")

# ConfigMap file path
INFO_FILE = os.getenv("INFO_FILE", "/usr/src/app/config/information.txt")

# Message from env variable
MESSAGE = os.getenv("MESSAGE", "")


def get_pingpong_count():
    """Get ping-pong count via HTTP from PingPong service"""
    try:
        with urllib.request.urlopen(PINGPONG_URL, timeout=5) as response:
            return int(response.read().decode().strip())
    except Exception as e:
        print(f"Error fetching pingpong count: {e}")
        return 0


def read_info_file():
    """Read content from information.txt"""
    try:
        with open(INFO_FILE, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "file not found"


class LogHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/status":
            try:
                with open(LOG_FILE, "r") as f:
                    # read last line
                    log_content = f.readlines()[-1].strip()
                
                pingpong_count = get_pingpong_count()
                file_content = read_info_file()
                
                # Format output with file content, env variable, timestamp and pings
                response = f"file content: {file_content}\n"
                response += f"env variable: MESSAGE={MESSAGE}\n"
                response += f"{log_content}\n"
                response += f"Ping / Pongs: {pingpong_count}"
                
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
