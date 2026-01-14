from fastapi import FastAPI
from app.db.base import Base  # registra models
from app.db.session import engine

from app.modules.auth.router import router as auth_router
from app.modules.reflections.router import router as reflections_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="EloMind API", version="0.1.0")

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(reflections_router, prefix="/reflections", tags=["Reflections"])

@app.get("/health")
def health():
    return {"status": "ok"}
