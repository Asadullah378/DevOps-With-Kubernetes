import os
import time
import psycopg2
from http.server import HTTPServer, BaseHTTPRequestHandler

# Database configuration
DB_HOST = os.getenv("DB_HOST", "postgres-svc")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "pingpong")
DB_USER = os.getenv("DB_USER", "pingpong")
DB_PASSWORD = os.getenv("DB_PASSWORD", "pingpong")


def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )


def init_db():
    """Initialize database table"""
    retries = 10
    while retries > 0:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS counter (
                    id INTEGER PRIMARY KEY,
                    count INTEGER NOT NULL DEFAULT 0
                )
            """)
            cur.execute("""
                INSERT INTO counter (id, count) VALUES (1, 0)
                ON CONFLICT (id) DO NOTHING
            """)
            conn.commit()
            cur.close()
            conn.close()
            print("Database initialized successfully")
            return
        except Exception as e:
            print(f"Database connection failed, retrying... ({e})")
            retries -= 1
            time.sleep(2)
    print("Failed to initialize database")


def get_counter():
    """Get current counter value from database"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT count FROM counter WHERE id = 1")
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result[0] if result else 0
    except Exception as e:
        print(f"Error getting counter: {e}")
        return 0


def increment_counter():
    """Increment counter in database and return new value"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE counter SET count = count + 1 WHERE id = 1 RETURNING count")
        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return result[0] if result else 0
    except Exception as e:
        print(f"Error incrementing counter: {e}")
        return 0


class PingPongHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/pingpong":
            counter = get_counter()
            response = f"pong {counter}"
            increment_counter()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(response.encode())
        elif self.path == "/pings":
            # Endpoint for LogOutput to get the current count
            counter = get_counter()
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
    init_db()
    port = int(os.getenv("PORT", 3000))
    print(f"Server started in port {port}")
    server = HTTPServer(("0.0.0.0", port), PingPongHandler)
    server.serve_forever()
