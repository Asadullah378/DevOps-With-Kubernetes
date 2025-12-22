import os
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

# In-memory storage for todos
todos: list[dict] = []


class TodoCreate(BaseModel):
    todo: str = Field(..., max_length=140)


@app.get("/todos")
async def get_todos():
    """Get all todos"""
    return todos


@app.post("/todos")
async def create_todo(todo_data: TodoCreate):
    """Create a new todo"""
    if len(todo_data.todo) > 140:
        raise HTTPException(status_code=400, detail="Todo must be 140 characters or less")
    
    new_todo = {"id": len(todos) + 1, "todo": todo_data.todo}
    todos.append(new_todo)
    print(f"Created todo: {new_todo}")
    return new_todo


if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    print(f"Server started in port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)

