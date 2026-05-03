from app.db.base_class import Base

# Importa models aqui para registrar no metadata

from app.modules.users.model import User  # noqa: F401
from app.modules.reflections.model import Reflection  # noqa: F401
from app.modules.feedback.model import Feedback  # noqa: F401
from app.modules.invitations.model import Invitation  # noqa: F401
from app.modules.therapist_clients.model import TherapistClient  # noqa: F401
from app.modules.consents.model import Consent  # noqa: F401
from app.modules.auth.password_reset.model import PasswordResetToken  # noqa: F401
from app.modules.anamnesis.model import Anamnesis  # noqa: F401
from app.modules.dreams.model import Dream  # noqa: F401
from app.modules.data_deletion_requests.model import DataDeletionRequest  # noqa: F401
from app.modules.push_tokens.model import UserPushToken  # noqa: F401
