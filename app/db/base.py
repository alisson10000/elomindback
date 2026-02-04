from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Importa models aqui para registrar no metadata
from app.modules.users.model import User  # noqa: F401
from app.modules.reflections.model import Reflection  # noqa: F401
from app.modules.feedback.model import Feedback  # noqa: F401
from app.modules.invitations.model import Invitation  # noqa: F401
from app.modules.therapist_clients.model import TherapistClient  # noqa: F401  ✅
