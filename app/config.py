import os
from dotenv import load_dotenv

load_dotenv()

# ===========================
# BANCO DE DADOS
# ===========================
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:@localhost:3306/elomind"
)

# ===========================
# JWT
# ===========================
JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_ME")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

# ===========================
# OPENAI
# ===========================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ===========================
# EMAIL / SMTP
# ===========================
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))


print("SMTP CONFIG:", SMTP_USER, SMTP_HOST, SMTP_PORT)
