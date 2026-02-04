import smtplib
from email.message import EmailMessage
from app.config import SMTP_USER, SMTP_PASSWORD


def send_email(to: str, subject: str, body: str):
    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
