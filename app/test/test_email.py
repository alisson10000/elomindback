import smtplib
import socket

from app.core.email import send_email

try:
    send_email(
        to="alisson.lima.souza@gmail.com",
        subject="Teste EloMind SMTP",
        body="Se você recebeu este email, o envio está funcionando."
    )
    print("✅ Email enviado com sucesso!")
except smtplib.SMTPAuthenticationError as e:
    print("❌ SMTPAuthenticationError (senha/conta recusada)")
    print("code:", getattr(e, "smtp_code", None))
    print("error:", getattr(e, "smtp_error", None))
except smtplib.SMTPConnectError as e:
    print("❌ SMTPConnectError (falha ao conectar)")
    print(e)
except smtplib.SMTPServerDisconnected as e:
    print("❌ SMTPServerDisconnected (conexão caiu)")
    print(e)
except smtplib.SMTPException as e:
    print("❌ SMTPException (erro SMTP genérico)")
    print(type(e), e)
except (socket.gaierror, TimeoutError, ConnectionError) as e:
    print("❌ Erro de rede/DNS/timeout")
    print(type(e), e)
except Exception as e:
    print("❌ Erro inesperado")
    print(type(e), e)
