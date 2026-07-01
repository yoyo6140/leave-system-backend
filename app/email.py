import os
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType

_conf = ConnectionConfig(
    MAIL_USERNAME   = os.getenv("MAIL_USERNAME", ""),
    MAIL_PASSWORD   = os.getenv("MAIL_PASSWORD", ""),
    MAIL_FROM       = os.getenv("MAIL_FROM", "no-reply@example.com"),
    MAIL_FROM_NAME  = os.getenv("MAIL_FROM_NAME", "請假系統"),
    MAIL_PORT       = int(os.getenv("MAIL_PORT", 587)),
    MAIL_SERVER     = os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_STARTTLS   = True,
    MAIL_SSL_TLS    = False,
    USE_CREDENTIALS = True,
)

_mailer = FastMail(_conf)


async def send_reset_password_email(to: str, token: str) -> None:
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    reset_link   = f"{frontend_url}/reset-password?token={token}"

    body = f"""
    <p>您好，</p>
    <p>我們收到您的密碼重設請求，請點擊以下連結重設密碼（連結將於 30 分鐘後失效）：</p>
    <p><a href="{reset_link}">{reset_link}</a></p>
    <p>若您未發出此請求，請忽略此信件。</p>
    """

    message = MessageSchema(
        subject    = "【請假系統】密碼重設",
        recipients = [to],
        body       = body,
        subtype    = MessageType.html,
    )
    await _mailer.send_message(message)
