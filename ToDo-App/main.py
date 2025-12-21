import os
import time
import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path

app = FastAPI(title="ToDo App")

# Configuration
IMAGE_DIR = Path(os.getenv("IMAGE_DIR", "/usr/src/app/images"))
IMAGE_FILE = IMAGE_DIR / "daily_image.jpg"
TIMESTAMP_FILE = IMAGE_DIR / "timestamp.txt"
CACHE_DURATION = 60 * 10  # 10 minutes in seconds


def ensure_image_dir():
    """Ensure the image directory exists"""
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)


def get_cached_timestamp():
    """Get the timestamp when image was last fetched"""
    try:
        return float(TIMESTAMP_FILE.read_text().strip())
    except (FileNotFoundError, ValueError):
        return 0


def save_timestamp():
    """Save current timestamp"""
    TIMESTAMP_FILE.write_text(str(time.time()))


def is_image_expired():
    """Check if the cached image is older than 10 minutes"""
    cached_time = get_cached_timestamp()
    return (time.time() - cached_time) > CACHE_DURATION


def fetch_new_image():
    """Fetch a new random image from Lorem Picsum"""
    try:
        print("Fetching new image from Lorem Picsum...")
        with httpx.Client(follow_redirects=True, timeout=30.0) as client:
            response = client.get("https://picsum.photos/1200")
            response.raise_for_status()
            IMAGE_FILE.write_bytes(response.content)
            save_timestamp()
            print("New image cached successfully")
            return True
    except Exception as e:
        print(f"Error fetching image: {e}")
        return False


def get_or_refresh_image():
    """Get cached image or fetch new one if expired"""
    ensure_image_dir()
    
    # If image doesn't exist, fetch it
    if not IMAGE_FILE.exists():
        fetch_new_image()
        return
    
    # If image is expired, fetch new one
    if is_image_expired():
        fetch_new_image()


@app.get("/image")
async def get_image():
    """Serve the cached image"""
    get_or_refresh_image()
    
    if IMAGE_FILE.exists():
        return FileResponse(IMAGE_FILE, media_type="image/jpeg")
    else:
        return HTMLResponse(content="<p>Image not available</p>", status_code=503)


@app.get("/", response_class=HTMLResponse)
async def root():
    # Ensure image is ready
    get_or_refresh_image()
    
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ToDo App</title>
        <style>
            body {
                font-family: sans-serif;
                text-align: center;
                padding: 20px;
            }
            img {
                max-width: 600px;
                width: 100%;
                margin-top: 20px;
            }
        </style>
    </head>
    <body>
        <h1>ToDo App</h1>
        <img src="/image" alt="Daily image" />
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    print(f"Server started in port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
