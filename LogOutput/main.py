import uuid
import time
from datetime import datetime, timezone


def main():
    # Generate random string on startup and store in memory
    random_string = str(uuid.uuid4())
    
    # Output every 5 seconds with timestamp
    while True:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") +  f"{datetime.now(timezone.utc).microsecond // 1000:03d}Z"
        print(f"{timestamp}: {random_string}")
        time.sleep(5)


if __name__ == "__main__":
    main()

