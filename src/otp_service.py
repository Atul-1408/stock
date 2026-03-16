"""OTP generation and email sending service.

Uses Gmail SMTP with App Password to send 6-digit OTP codes.
"""

import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config import Config


def generate_otp() -> str:
    """Generate a random 6-digit OTP code."""
    return str(random.randint(100000, 999999))


def send_otp_email(recipient_email: str, otp_code: str) -> bool:
    """Send an OTP code to the recipient via Gmail SMTP.

    Returns True if the email was sent successfully, False otherwise.
    """
    sender_email = Config.GMAIL_SENDER
    app_password = Config.GMAIL_APP_PASSWORD

    if not sender_email or not app_password:
        print("ERROR: Gmail credentials not configured in .env")
        return False

    # Build the email
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🔐 Your Login OTP: {otp_code} — Sovereign Intelligence"
    msg["From"] = f"Sovereign Intelligence <{sender_email}>"
    msg["To"] = recipient_email

    # Plain text fallback
    text_body = f"""Your one-time login code is: {otp_code}

This code expires in 5 minutes. Do not share it with anyone.

— Sovereign Intelligence"""

    # Rich HTML email
    html_body = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 480px; margin: 0 auto; background: #0A0B10; border-radius: 16px; overflow: hidden; border: 1px solid #1e293b;">
        <div style="background: linear-gradient(135deg, #3b82f6, #8b5cf6); padding: 32px 24px; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 24px; font-weight: 800;">🔐 Login Verification</h1>
            <p style="color: rgba(255,255,255,0.85); margin: 8px 0 0; font-size: 14px;">Sovereign Intelligence</p>
        </div>
        <div style="padding: 32px 24px; text-align: center;">
            <p style="color: #94a3b8; font-size: 14px; margin: 0 0 24px;">Enter this code to complete your login:</p>
            <div style="background: #1e293b; border: 2px solid #3b82f6; border-radius: 12px; padding: 20px; display: inline-block;">
                <span style="font-size: 36px; font-weight: 800; letter-spacing: 8px; color: #f8fafc; font-family: 'Courier New', monospace;">{otp_code}</span>
            </div>
            <p style="color: #64748b; font-size: 12px; margin: 24px 0 0;">This code expires in <strong style="color: #f59e0b;">5 minutes</strong>.</p>
            <p style="color: #475569; font-size: 11px; margin: 16px 0 0;">If you didn't request this code, please ignore this email.</p>
        </div>
        <div style="background: #0f172a; padding: 16px 24px; text-align: center; border-top: 1px solid #1e293b;">
            <p style="color: #475569; font-size: 11px; margin: 0;">© Sovereign Intelligence — Stock Sense Platform</p>
        </div>
    </div>
    """

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, app_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        print(f"OTP email sent to {recipient_email}")
        return True
    except Exception as e:
        print(f"ERROR sending OTP email: {e}")
        return False
