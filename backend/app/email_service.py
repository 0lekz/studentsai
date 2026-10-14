"""
Email service for sending verification emails using SendGrid Web API
"""

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, HtmlContent
from pydantic import EmailStr
import jwt
from datetime import datetime, timedelta
from typing import Optional
from .config import settings
from .database import get_db, Session
from .auth import get_user_by_email, get_user_by_id
import uuid


def get_sendgrid_client():
    """Get SendGrid client with current configuration"""
    return SendGridAPIClient(api_key=settings.sendgrid_api_key)


def send_email_via_sendgrid(to_email: str, subject: str, html_content: str):
    """Send email using SendGrid Web API"""
    try:
        message = Mail(
            from_email=settings.mail_from,
            to_emails=to_email,
            subject=subject,
            html_content=html_content,
        )

        sg = get_sendgrid_client()
        response = sg.send(message)

        if response.status_code in [200, 201, 202]:
            print(f"Successfully sent email to {to_email} via SendGrid")
            return True
        else:
            print(f"SendGrid API error: {response.status_code} - {response.body}")
            return False

    except Exception as e:
        print(f"SendGrid email sending failed: {str(e)}")
        return False


def create_verification_token(email: str) -> str:
    """Create a JWT token for email verification"""
    expiration = datetime.utcnow() + timedelta(
        minutes=settings.verification_token_expire_minutes
    )

    payload = {"email": email, "exp": expiration, "type": "email_verification"}

    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return token


def create_password_reset_token(email: str) -> str:
    """Create a JWT token for password reset"""
    expiration = datetime.utcnow() + timedelta(
        minutes=settings.verification_token_expire_minutes
    )

    payload = {"email": email, "exp": expiration, "type": "password_reset"}

    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return token


def verify_password_reset_token(token: str) -> Optional[str]:
    """Verify and decode the password reset token, return email if valid"""
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        if payload.get("type") != "password_reset":
            return None
        return payload.get("email")
    except jwt.ExpiredSignatureError:
        return None
    except jwt.JWTError:
        return None


def verify_verification_token(token: str) -> Optional[str]:
    """Verify and decode the verification token, return email if valid"""
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )

        # Check if token is for email verification
        if payload.get("type") != "email_verification":
            return None

        return payload.get("email")
    except jwt.ExpiredSignatureError:
        return None
    except jwt.JWTError:
        return None


async def send_verification_email(email: str, username: str, verification_url: str):
    """Send verification email to user"""
    import asyncio

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Verify Your Email - StudentsAI</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f8f9fa;
            }}
            .container {{
                background-color: white;
                padding: 40px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
            }}
            .logo {{
                font-size: 24px;
                font-weight: bold;
                color: #f97316;
                margin-bottom: 10px;
            }}
            .verification-button {{
                display: inline-block;
                background-color: #f97316;
                color: white;
                padding: 12px 24px;
                text-decoration: none;
                border-radius: 6px;
                font-weight: 500;
                margin: 20px 0;
            }}
            .verification-button:hover {{
                background-color: #ea580c;
            }}
            .footer {{
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #e5e7eb;
                font-size: 14px;
                color: #6b7280;
                text-align: center;
            }}
            .warning {{
                background-color: #fef3c7;
                border: 1px solid #f59e0b;
                border-radius: 6px;
                padding: 15px;
                margin: 20px 0;
                color: #92400e;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">StudentsAI</div>
                <h1>Verify Your Email Address</h1>
            </div>
            
            <p>Hi {username},</p>
            
            <p>Welcome to StudentsAI! To complete your registration and start using our learning platform, please verify your email address by clicking the button below:</p>
            
            <div style="text-align: center;">
                <a href="{verification_url}" class="verification-button">Verify Email Address</a>
            </div>
            
            <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
            <p style="word-break: break-all; color: #6b7280;">{verification_url}</p>
            
            <div class="warning">
                <strong>Security Notice:</strong> This verification link will expire in {settings.verification_token_expire_minutes} minutes. 
                If you didn't create an account with StudentsAI, please ignore this email.
            </div>
            
            <p>After verification, you'll have access to all our features including:</p>
            <ul>
                <li>Smart note-taking and organization</li>
                <li>AI-powered flashcard generation</li>
                <li>Knowledge graph visualization</li>
                <li>Spaced repetition learning</li>
            </ul>
            
            <p>If you have any questions, feel free to reach out to our support team.</p>
            
            <p>Best regards,<br>The StudentsAI Team</p>
            
            <div class="footer">
                <p>This email was sent to {email}. If you didn't sign up for StudentsAI, please ignore this message.</p>
                <p>&copy; 2024 StudentsAI. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """

    try:
        print(f"Attempting to send verification email to {email}")

        # Send email using SendGrid Web API
        success = send_email_via_sendgrid(
            to_email=email,
            subject="Verify Your Email - StudentsAI",
            html_content=html_content,
        )

        if success:
            print(f"Successfully sent verification email to {email}")
        else:
            raise Exception("SendGrid email sending failed")

    except Exception as e:
        print(f"Verification email send failed for {email}: {str(e)}")
        raise Exception(f"Email sending failed: {str(e)}")


async def send_password_change_notification(email: str, username: str):
    """Send notification when password is changed"""

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Password Changed - StudentsAI</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f8f9fa;
            }}
            .container {{
                background-color: white;
                padding: 40px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
            }}
            .logo {{
                font-size: 24px;
                font-weight: bold;
                color: #f97316;
                margin-bottom: 10px;
            }}
            .warning {{
                background-color: #fef3c7;
                border: 1px solid #f59e0b;
                border-radius: 6px;
                padding: 15px;
                margin: 20px 0;
                color: #92400e;
            }}
            .footer {{
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #e5e7eb;
                font-size: 14px;
                color: #6b7280;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">StudentsAI</div>
                <h1>Password Changed Successfully</h1>
            </div>
            
            <p>Hi {username},</p>
            
            <p>Your StudentsAI account password has been changed successfully.</p>
            
            <div class="warning">
                <strong>Security Notice:</strong> If you didn't change your password, please contact our support team immediately. 
                For security reasons, you have been logged out of all other devices.
            </div>
            
            <p>If you made this change, you can safely ignore this email.</p>
            
            <p>Best regards,<br>The StudentsAI Team</p>
            
            <div class="footer">
                <p>This email was sent to {email}.</p>
                <p>&copy; 2024 StudentsAI. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """

    if not send_email_via_sendgrid(
        to_email=email,
        subject="Password Changed - StudentsAI",
        html_content=html_content,
    ):
        raise Exception("SendGrid email sending failed")


async def send_password_reset_email(email: str, reset_url: str):
    """Send password reset email"""
    html_content = f"""
    <html>
      <body>
        <h2>Reset Your Password</h2>
        <p>Click the link below to reset your password:</p>
        <p><a href="{reset_url}">Reset Password</a></p>
        <p>If you did not request this, you can ignore this email.</p>
      </body>
    </html>
    """

    if not send_email_via_sendgrid(
        to_email=email,
        subject="Reset Your Password - StudentsAI",
        html_content=html_content,
    ):
        raise Exception("SendGrid email sending failed")


async def send_account_deletion_email(email: str, confirm_url: str):
    """Send account deletion confirmation email"""
    import asyncio

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Confirm Account Deletion - StudentsAI</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f8f9fa;
            }}
            .container {{
                background-color: white;
                padding: 40px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
            }}
            .logo {{
                font-size: 24px;
                font-weight: bold;
                color: #f97316;
                margin-bottom: 10px;
            }}
            .delete-button {{
                display: inline-block;
                background-color: #dc2626;
                color: white;
                padding: 12px 24px;
                text-decoration: none;
                border-radius: 6px;
                font-weight: 500;
                margin: 20px 0;
            }}
            .warning {{
                background-color: #fef2f2;
                border-left: 4px solid #dc2626;
                padding: 15px;
                margin: 20px 0;
                border-radius: 4px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">StudentsAI</div>
                <h2>Confirm Account Deletion</h2>
            </div>
            
            <div class="warning">
                <strong>⚠️ Important:</strong> This action is permanent and cannot be undone.
            </div>
            
            <p>You requested to delete your StudentsAI account. This will permanently remove:</p>
            <ul>
                <li>All your notes and study materials</li>
                <li>Generated flashcards and summaries</li>
                <li>Study progress and statistics</li>
                <li>Account settings and preferences</li>
            </ul>
            
            <p>If you're sure you want to proceed, click the button below:</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{confirm_url}" class="delete-button">
                    Confirm Account Deletion
                </a>
            </div>
            
            <p><strong>If you didn't request this deletion, please ignore this email.</strong> Your account will remain safe and unchanged.</p>
            
            <p style="color: #666; font-size: 14px; margin-top: 30px;">
                This link will expire in 24 hours for security purposes.
            </p>
        </div>
    </body>
    </html>
    """

    try:
        # Send email using SendGrid Web API
        success = send_email_via_sendgrid(
            to_email=email,
            subject="Confirm Account Deletion - StudentsAI",
            html_content=html_content,
        )

        if not success:
            raise Exception("SendGrid email sending failed")

    except Exception as e:
        print(f"Account deletion email send failed for {email}: {str(e)}")
        raise


async def send_email_change_verification_step1(
    db: Session, user_id: uuid.UUID, current_email: str, new_email: str
) -> bool:
    """Step 1: Send verification to current email to confirm ownership"""
    try:
        # Create verification token for current email
        token_data = {
            "sub": current_email,
            "new_email": new_email,
            "user_id": str(user_id),
            "type": "email_change_step1",
            "exp": datetime.utcnow()
            + timedelta(minutes=settings.verification_token_expire_minutes),
        }

        token = jwt.encode(
            token_data, settings.secret_key, algorithm=settings.algorithm
        )

        # Create pending email change record
        from .database import PendingEmailChange

        pending_change = PendingEmailChange(
            user_id=user_id,
            current_email=current_email,
            new_email=new_email,
            expires_at=datetime.utcnow() + timedelta(hours=24),  # 24 hour expiry
        )
        db.add(pending_change)
        db.commit()

        # Send verification email to current email
        verification_url = f"{settings.frontend_url}/verify-email-change-step1/{token}?new_email={new_email}"

        html_content = f"""
            <html>
                <body>
                    <h2>Email Change Request</h2>
                    <p>You have requested to change your email address from <strong>{current_email}</strong> to <strong>{new_email}</strong>.</p>
                    <p>To confirm this change, please click the link below:</p>
                    <p><a href="{verification_url}">Confirm Email Change</a></p>
                    <p>This link will expire in {settings.verification_token_expire_minutes} minutes.</p>
                    <p>If you did not request this change, please ignore this email.</p>
                </body>
            </html>
            """
        if not send_email_via_sendgrid(
            to_email=current_email,
            subject="Confirm Email Change Request",
            html_content=html_content,
        ):
            raise Exception("SendGrid email sending failed")
        return True

    except Exception as e:
        db.rollback()
        if settings.debug:
            print(f"Error sending email change verification step 1: {e}")
        return False


async def send_email_change_verification_step2(
    db: Session, user_id: uuid.UUID, new_email: str
) -> bool:
    """Step 2: Send verification to new email after current email is verified"""
    try:
        # Create verification token for new email
        token_data = {
            "sub": new_email,
            "user_id": str(user_id),
            "type": "email_change_step2",
            "exp": datetime.utcnow()
            + timedelta(minutes=settings.verification_token_expire_minutes),
        }

        token = jwt.encode(
            token_data, settings.secret_key, algorithm=settings.algorithm
        )

        # Send verification email to new email
        verification_url = f"{settings.frontend_url}/verify-email-change-step2/{token}?current_email={get_user_by_id(db, user_id).email}"

        html_content = f"""
            <html>
                <body>
                    <h2>Verify New Email Address</h2>
                    <p>You have requested to change your email address to <strong>{new_email}</strong>.</p>
                    <p>To complete this change, please click the link below:</p>
                    <p><a href="{verification_url}">Verify New Email</a></p>
                    <p>This link will expire in {settings.verification_token_expire_minutes} minutes.</p>
                    <p>If you did not request this change, please ignore this email.</p>
                </body>
            </html>
            """
        if not send_email_via_sendgrid(
            to_email=new_email,
            subject="Verify New Email Address",
            html_content=html_content,
        ):
            raise Exception("SendGrid email sending failed")
        return True

    except Exception as e:
        if settings.debug:
            print(f"Error sending email change verification step 2: {e}")
        return False


def verify_email_change_token(token: str) -> Optional[dict]:
    """Verify email change token and return payload"""
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
