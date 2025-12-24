import os
import sys
import time
import logging
import json
import psycopg2
import uvicorn
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
                    todo VARCHAR(140) NOT NULL
                )
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


@app.get("/todos")
async def get_todos():
    """Get all todos from database"""
    logger.info("Fetching all todos")
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, todo FROM todos ORDER BY id")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        todos = [{"id": row[0], "todo": row[1]} for row in rows]
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
            "INSERT INTO todos (todo) VALUES (%s) RETURNING id, todo",
            (todo_data.todo,)
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        new_todo = {"id": row[0], "todo": row[1]}
        logger.info(f"SUCCESS: Created todo with id={new_todo['id']}")
        return new_todo
    except Exception as e:
        logger.error(f"Error creating todo: {e}")
        raise HTTPException(status_code=500, detail="Database error")


@app.get("/")
async def root():
    """Root endpoint for health checks"""
    return {"status": "ok"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    logger.info("Starting ToDo Backend...")
    init_db()
    port = int(os.getenv("PORT", 3000))
    logger.info(f"Server started in port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
