import uvicorn


def dev() -> None:
    """Start the FastAPI dev server with hot-reload."""
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


def start() -> None:
    """Start the FastAPI server without reload."""
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
