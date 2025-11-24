from fastapi import FastAPI

app = FastAPI(title="Backend FastAPI Scaffold")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

