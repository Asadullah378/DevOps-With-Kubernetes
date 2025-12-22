import os
from http.server import HTTPServer, BaseHTTPRequestHandler

# Counter in memory
counter = 0


class PingPongHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global counter
        if self.path == "/pingpong":
            response = f"pong {counter}"
            counter += 1
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(response.encode())
        elif self.path == "/pings":
            # Endpoint for LogOutput to get the current count
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(str(counter).encode())
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
