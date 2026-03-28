from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.base import Base
from app.db.session import engine

from app.modules.auth.router import router as auth_router
from app.modules.auth.password_reset.router import router as password_reset_router
from app.modules.reflections.router import router as reflections_router
from app.modules.feedback.router import router as feedback_router
from app.modules.users.router import router as users_router
from app.modules.invitations.router import router as invitations_router
from app.modules.consents.router import router as consents_router
from app.modules.anamnesis.router import router as anamnesis_router
from app.modules.dreams.router import router as dreams_router
from app.modules.data_deletion_requests.router import router as data_deletion_router
from app.modules.push_tokens.router import router as push_tokens_router

app = FastAPI(
    title="EloMind API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# =========================
# CORS
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# Startup
# =========================
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    print("✅ Banco de dados inicializado")

# =========================
# Routers
# =========================

# Auth
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(password_reset_router, prefix="/auth", tags=["Auth"])

# App (core)
app.include_router(reflections_router, prefix="/reflections", tags=["Reflections"])
app.include_router(feedback_router, prefix="/feedback", tags=["Feedback"])

# Push Tokens
app.include_router(push_tokens_router, prefix="/push-tokens", tags=["Push Tokens"])

# Users / convites / termos
app.include_router(users_router)
app.include_router(invitations_router)
app.include_router(consents_router)

# Anamnese
app.include_router(anamnesis_router, prefix="/anamnesis", tags=["Anamnesis"])

# Sonhos (RF005)
app.include_router(dreams_router, prefix="/dreams", tags=["Dreams"])

# LGPD: Solicitação de exclusão total (MVP manual)
# Endpoint: POST /data-deletion-request
app.include_router(data_deletion_router, tags=["LGPD"])

# =========================
# Health
# =========================
@app.get("/health")
def health():
    return {"status": "ok"}