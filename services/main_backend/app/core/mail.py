import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
from app.core.logging import request_logger, error_logger


def send_otp_email(recipient_email: str, recipient_name: str, otp_code: str, purpose: str = "registration") -> bool:
    """
    Sends a professional OTP email to recipient via SMTP.
    Uses environment variables for SMTP credentials.

    IMPORTANT: For email delivery to work, configure these in .env:
    - SMTP_HOST (e.g., smtp.gmail.com)
    - SMTP_PORT (e.g., 587 for TLS, 465 for SSL)
    - SMTP_USERNAME (your email address)
    - SMTP_PASSWORD (your app-specific password, NOT regular password)
    - SMTP_FROM_EMAIL (sender email)
    - SMTP_FROM_NAME (sender name)

    For Gmail: Generate an App Password at https://myaccount.google.com/apppasswords
    """
    # Log OTP code in development mode for testing
    if settings.ENVIRONMENT == "development":
        request_logger.info(
            f"[DEV MODE] OTP Code for {recipient_email} ({purpose}): {otp_code}"
        )

    if not settings.SMTP_PASSWORD or not settings.SMTP_USERNAME:
        request_logger.error(
            f"SMTP credentials not configured in environment. Email delivery FAILED for {recipient_email}. "
            f"Please configure SMTP_USERNAME and SMTP_PASSWORD in .env file. "
            f"OTP Code for {recipient_email} ({purpose}): {otp_code}"
        )
        return False

    title = "Verify Your Account" if purpose == "registration" else "Reset Your Password"
    action_text = "confirming your email address" if purpose == "registration" else "resetting your password"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>{title} — CNC Design Generator</title>
      <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 40px 20px; }}
        .container {{ max-width: 540px; margin: 0 auto; background-color: #1e293b; border: 1px solid #334155; border-radius: 16px; overflow: hidden; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5); }}
        .header {{ background-color: #0284c7; padding: 32px 24px; text-align: center; background-image: linear-gradient(135deg, #0284c7 0%, #4f46e5 100%); }}
        .header h1 {{ margin: 0; font-size: 24px; font-weight: 800; color: #ffffff; letter-spacing: -0.5px; }}
        .header p {{ margin: 6px 0 0 0; font-size: 13px; color: #e0f2fe; opacity: 0.9; }}
        .content {{ padding: 36px 32px; text-align: center; }}
        .greeting {{ font-size: 16px; color: #cbd5e1; margin-bottom: 16px; text-align: left; }}
        .instruction {{ font-size: 14px; color: #94a3b8; line-height: 1.6; margin-bottom: 28px; text-align: left; }}
        .code-box {{ background-color: #0f172a; border: 2px dashed #0284c7; border-radius: 12px; padding: 20px; margin: 24px 0; text-align: center; }}
        .code {{ font-family: 'Courier New', Courier, monospace; font-size: 36px; font-weight: 800; letter-spacing: 10px; color: #38bdf8; margin: 0; }}
        .expire-notice {{ font-size: 12px; color: #64748b; margin-top: 10px; }}
        .security-warning {{ background-color: #0f172a; border-left: 4px solid #f59e0b; padding: 12px 16px; text-align: left; border-radius: 4px; font-size: 12px; color: #e2e8f0; margin-top: 28px; }}
        .footer {{ padding: 24px; text-align: center; font-size: 11px; color: #64748b; border-top: 1px solid #334155; background-color: #0f172a; }}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1>CNC DESIGN GENERATOR</h1>
          <p>AI CAD & Manufacturing Engineering Suite</p>
        </div>
        <div class="content">
          <div class="greeting">Hello {recipient_name},</div>
          <div class="instruction">
            Use the verification code below to complete {action_text} for your CNC Design Generator account.
          </div>

          <div class="code-box">
            <div class="code">{otp_code}</div>
            <div class="expire-notice">This code expires in {settings.OTP_EXPIRE_MINUTES} minutes.</div>
          </div>

          <div class="security-warning">
            <strong>Security Notice:</strong> Never share this code with anyone. CNC Design Generator staff will never ask for your verification code.
          </div>
        </div>
        <div class="footer">
          &copy; CNC Design Generator Inc. All rights reserved. <br/>
          If you did not request this code, please ignore this email.
        </div>
      </div>
    </body>
    </html>
    """

    plain_content = f"""
    CNC DESIGN GENERATOR — {title.upper()}

    Hello {recipient_name},

    Your verification code is: {otp_code}

    This code will expire in {settings.OTP_EXPIRE_MINUTES} minutes.

    If you did not request this code, please ignore this email.
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"{otp_code} is your CNC Design Generator verification code"
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = recipient_email

        msg.attach(MIMEText(plain_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        if settings.SMTP_PORT == 465:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM_EMAIL, [recipient_email], msg.as_string())
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM_EMAIL, [recipient_email], msg.as_string())

        request_logger.info(f"Successfully sent OTP email to {recipient_email}")
        return True
    except Exception as e:
        error_logger.error(f"Failed to send OTP email to {recipient_email}: {str(e)}", exc_info=e)
        return False
