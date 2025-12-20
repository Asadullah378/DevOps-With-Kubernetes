import os
import uvicorn
from fastapi import FastAPI

app = FastAPI(title="ToDo App")


@app.get("/")
async def root():
    return {"message": "ToDo App"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    print(f"Server started in port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)

