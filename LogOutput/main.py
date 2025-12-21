import uuid
import os
import threading
import time
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

# Generate random string on startup and store in memory
random_string = str(uuid.uuid4())


def get_timestamp():
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def log_output():
    """Background thread that outputs timestamp and random string every 5 seconds"""
    while True:
        print(f"{get_timestamp()}: {random_string}")
        time.sleep(5)


class StatusHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/status":
            response = {
                "timestamp": get_timestamp(),
                "random_string": random_string
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress default HTTP request logging
        pass


if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    
    # Start background logging thread
    log_thread = threading.Thread(target=log_output, daemon=True)
    log_thread.start()
    
    print(f"Server started in port {port}")
    server = HTTPServer(("0.0.0.0", port), StatusHandler)
    server.serve_forever()
