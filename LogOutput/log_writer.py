import uuid
import os
import time
from datetime import datetime, timezone

# Generate random string on startup
random_string = str(uuid.uuid4())

# File path for shared volume
LOG_FILE = os.getenv("LOG_FILE", "/usr/src/app/files/log.txt")


def get_timestamp():
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


if __name__ == "__main__":
    print(f"Log Writer started. Random string: {random_string}")
    
    while True:
        log_line = f"{get_timestamp()}: {random_string}\n"
        print(log_line)
        
        # Append to shared file
        with open(LOG_FILE, "a") as f:
            f.write(log_line)
        
        time.sleep(5)

