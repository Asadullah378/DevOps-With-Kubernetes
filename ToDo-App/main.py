import os
import time
import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path

app = FastAPI(title="ToDo App")

# Configuration from environment variables
IMAGE_DIR = Path(os.getenv("IMAGE_DIR", "/usr/src/app/images"))
IMAGE_FILE = IMAGE_DIR / "daily_image.jpg"
TIMESTAMP_FILE = IMAGE_DIR / "timestamp.txt"
CACHE_DURATION = int(os.getenv("CACHE_DURATION", "600"))  # seconds
IMAGE_URL = os.getenv("IMAGE_URL", "https://picsum.photos/1200")


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
        print(f"Fetching new image from {IMAGE_URL}...")
        with httpx.Client(follow_redirects=True, timeout=30.0) as client:
            response = client.get(IMAGE_URL)
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
                max-width: 800px;
                margin: 0 auto;
            }
            img {
                max-width: 400px;
                width: 100%;
                margin: 20px 0;
            }
            .todo-form {
                margin: 20px 0;
            }
            .todo-form input[type="text"] {
                width: 300px;
                padding: 10px;
                font-size: 16px;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            .todo-form button {
                padding: 10px 20px;
                font-size: 16px;
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                margin-left: 10px;
            }
            .todo-form button:hover {
                background-color: #0056b3;
            }
            .char-count {
                font-size: 12px;
                color: #666;
                margin-top: 5px;
            }
            .todo-list {
                list-style: none;
                padding: 0;
                text-align: left;
                max-width: 500px;
                margin: 20px auto;
            }
            .todo-list li {
                padding: 10px;
                border-bottom: 1px solid #eee;
            }
        </style>
    </head>
    <body>
        <h1>ToDo App</h1>
        <img src="/image" alt="Daily image" />
        
        <div class="todo-form">
            <input type="text" id="todoInput" maxlength="140" placeholder="Enter a todo (max 140 chars)" />
            <button onclick="addTodo()">Send</button>
            <div class="char-count"><span id="charCount">0</span>/140</div>
        </div>
        
        <ul class="todo-list" id="todoList">
            <li>Loading...</li>
        </ul>
        
        <script>
            const input = document.getElementById('todoInput');
            const charCount = document.getElementById('charCount');
            const todoList = document.getElementById('todoList');
            
            input.addEventListener('input', function() {
                charCount.textContent = this.value.length;
            });
            
            async function fetchTodos() {
                try {
                    const response = await fetch('/todos');
                    const todos = await response.json();
                    renderTodos(todos);
                } catch (error) {
                    console.error('Error fetching todos:', error);
                    todoList.innerHTML = '<li>Error loading todos</li>';
                }
            }
            
            function renderTodos(todos) {
                if (todos.length === 0) {
                    todoList.innerHTML = '<li>No todos yet. Add one!</li>';
                } else {
                    todoList.innerHTML = todos.map(t => `<li>${t.todo}</li>`).join('');
                }
            }
            
            async function addTodo() {
                const value = input.value.trim();
                if (value && value.length <= 140) {
                    try {
                        const response = await fetch('/todos', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ todo: value })
                        });
                        if (response.ok) {
                            input.value = '';
                            charCount.textContent = '0';
                            fetchTodos();
                        }
                    } catch (error) {
                        console.error('Error creating todo:', error);
                    }
                }
            }
            
            // Load todos on page load
            fetchTodos();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    print(f"Server started in port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
