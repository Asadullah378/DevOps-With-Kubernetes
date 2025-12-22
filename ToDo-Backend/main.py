import os
import time
import psycopg2
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

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
            print("Database initialized successfully")
            return
        except Exception as e:
            print(f"Database connection failed, retrying... ({e})")
            retries -= 1
            time.sleep(2)
    print("Failed to initialize database")


class TodoCreate(BaseModel):
    todo: str = Field(..., max_length=140)


@app.get("/todos")
async def get_todos():
    """Get all todos from database"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, todo FROM todos ORDER BY id")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [{"id": row[0], "todo": row[1]} for row in rows]
    except Exception as e:
        print(f"Error fetching todos: {e}")
        raise HTTPException(status_code=500, detail="Database error")


@app.post("/todos")
async def create_todo(todo_data: TodoCreate):
    """Create a new todo in database"""
    if len(todo_data.todo) > 140:
        raise HTTPException(status_code=400, detail="Todo must be 140 characters or less")
    
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
        print(f"Created todo: {new_todo}")
        return new_todo
    except Exception as e:
        print(f"Error creating todo: {e}")
        raise HTTPException(status_code=500, detail="Database error")


if __name__ == "__main__":
    init_db()
    port = int(os.getenv("PORT", 3000))
    print(f"Server started in port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
