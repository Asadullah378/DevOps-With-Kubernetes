import os
import sys
import time
import logging
import json
import asyncio
import psycopg2
import uvicorn
import nats
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="ToDo Backend")

# NATS configuration
NATS_URL = os.getenv("NATS_URL", "nats://my-nats:4222")
NATS_SUBJECT = "todos"
nats_client = None


async def get_nats_client():
    """Get or create NATS client connection"""
    global nats_client
    if nats_client is None or not nats_client.is_connected:
        try:
            nats_client = await nats.connect(servers=[NATS_URL])
            logger.info(f"Connected to NATS at {NATS_URL}")
        except Exception as e:
            logger.warning(f"Failed to connect to NATS: {e}")
            return None
    return nats_client


async def publish_todo_event(action: str, todo: dict):
    """Publish todo event to NATS"""
    try:
        nc = await get_nats_client()
        if nc is None:
            logger.warning("NATS not available, skipping event publish")
            return
        
        message = {
            "action": action,
            "todo": todo,
            "timestamp": datetime.utcnow().isoformat()
        }
        await nc.publish(NATS_SUBJECT, json.dumps(message).encode())
        logger.info(f"Published {action} event for todo {todo.get('id')} to NATS")
    except Exception as e:
        logger.error(f"Failed to publish to NATS: {e}")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database configuration
DB_HOST = os.getenv("DB_HOST", "todo-postgres-svc")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "tododb")
DB_USER = os.getenv("DB_USER", "todouser")
DB_PASSWORD = os.getenv("DB_PASSWORD", "todopassword")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests"""
    start_time = time.time()
    
    # Log request
    logger.info(f"REQUEST: {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    # Log response
    duration = time.time() - start_time
    logger.info(f"RESPONSE: {request.method} {request.url.path} - Status: {response.status_code} - Duration: {duration:.3f}s")
    
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors (like too long todos)"""
    error_details = exc.errors()
    
    # Check if it's a max_length error
    for error in error_details:
        if error.get('type') == 'string_too_long':
            logger.warning(f"BLOCKED: Todo exceeds 140 characters - Path: {request.url.path}")
            return JSONResponse(
                status_code=400,
                content={"detail": "Todo must be 140 characters or less"}
            )
    
    logger.warning(f"VALIDATION ERROR: {error_details}")
    return JSONResponse(
        status_code=422,
        content={"detail": error_details}
    )


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
                CREATE TABLE IF NOT EXISTS todos (
                    id SERIAL PRIMARY KEY,
                    todo VARCHAR(140) NOT NULL,
                    done BOOLEAN NOT NULL DEFAULT FALSE
                )
            """)
            # Add done column if it doesn't exist (for existing databases)
            cur.execute("""
                ALTER TABLE todos ADD COLUMN IF NOT EXISTS done BOOLEAN NOT NULL DEFAULT FALSE
            """)
            conn.commit()
            cur.close()
            conn.close()
            logger.info("Database initialized successfully")
            return
        except Exception as e:
            logger.warning(f"Database connection failed, retrying... ({e})")
            retries -= 1
            time.sleep(2)
    logger.error("Failed to initialize database")


class TodoCreate(BaseModel):
    todo: str = Field(..., max_length=140)


class TodoUpdate(BaseModel):
    done: bool


@app.get("/todos")
async def get_todos():
    """Get all todos from database"""
    logger.info("Fetching all todos")
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, todo, done FROM todos ORDER BY done, id")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        todos = [{"id": row[0], "todo": row[1], "done": row[2]} for row in rows]
        logger.info(f"Retrieved {len(todos)} todos")
        return todos
    except Exception as e:
        logger.error(f"Error fetching todos: {e}")
        raise HTTPException(status_code=500, detail="Database error")


@app.post("/todos")
async def create_todo(todo_data: TodoCreate):
    """Create a new todo in database"""
    # Additional check (Pydantic already validates, but double-check)
    if len(todo_data.todo) > 140:
        logger.warning(f"BLOCKED: Todo exceeds 140 characters - Length: {len(todo_data.todo)}")
        raise HTTPException(status_code=400, detail="Todo must be 140 characters or less")
    
    logger.info(f"Creating todo: '{todo_data.todo[:50]}...' (length: {len(todo_data.todo)})")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO todos (todo, done) VALUES (%s, FALSE) RETURNING id, todo, done",
            (todo_data.todo,)
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        new_todo = {"id": row[0], "todo": row[1], "done": row[2]}
        logger.info(f"SUCCESS: Created todo with id={new_todo['id']}")
        
        # Publish event to NATS
        await publish_todo_event("created", new_todo)
        
        return new_todo
    except Exception as e:
        logger.error(f"Error creating todo: {e}")
        raise HTTPException(status_code=500, detail="Database error")


@app.put("/todos/{todo_id}")
async def update_todo(todo_id: int, todo_data: TodoUpdate):
    """Update a todo's done status"""
    logger.info(f"Updating todo {todo_id}: done={todo_data.done}")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE todos SET done = %s WHERE id = %s RETURNING id, todo, done",
            (todo_data.done, todo_id)
        )
        row = cur.fetchone()
        if row is None:
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Todo not found")
        conn.commit()
        cur.close()
        conn.close()
        updated_todo = {"id": row[0], "todo": row[1], "done": row[2]}
        logger.info(f"SUCCESS: Updated todo {todo_id} - done={updated_todo['done']}")
        
        # Publish event to NATS
        await publish_todo_event("updated", updated_todo)
        
        return updated_todo
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating todo: {e}")
        raise HTTPException(status_code=500, detail="Database error")


@app.get("/")
async def root():
    """Root endpoint for health checks"""
    return {"status": "ok"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/healthz")
async def readiness_check():
    """Readiness probe - checks database connectivity"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Database connection failed: {e}")


if __name__ == "__main__":
    logger.info("Starting ToDo Backend...")
    init_db()
    port = int(os.getenv("PORT", 3000))
    logger.info(f"Server started in port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
