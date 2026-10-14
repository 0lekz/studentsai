"""
OAuth service for handling Google OAuth authentication
"""

import logging
from typing import Any

import requests
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from .auth import create_access_token
from .config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI
from .database import create_or_get_oauth_user

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GoogleOAuthService:
    """Service for handling Google OAuth authentication"""

    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    @classmethod
    def get_google_user_info(cls, code: str) -> dict[str, Any]:
        """Exchange authorization code for user info"""
        try:
            logger.info(f"Starting Google OAuth exchange for code: {code[:20]}...")

            # Exchange code for access token
            token_data = {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                # Must EXACTLY match the redirect used in the initial auth request
                "redirect_uri": GOOGLE_REDIRECT_URI,
            }

            logger.info(
                f"Making token request to Google with client_id: {GOOGLE_CLIENT_ID[:20]}..."
            )
            response = requests.post(cls.GOOGLE_TOKEN_URL, data=token_data)
            logger.info(f"Google token response status: {response.status_code}")

            if not response.ok:
                logger.error(
                    f"Google token request failed: {response.status_code} - {response.text}"
                )
                response.raise_for_status()

            token_response = response.json()
            access_token = token_response.get("access_token")

            if not access_token:
                logger.error(f"No access token in Google response: {token_response}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get access token from Google",
                )

            logger.info("Successfully obtained access token from Google")

            # Get user info using access token
            headers = {"Authorization": f"Bearer {access_token}"}
            logger.info("Requesting user info from Google")
            userinfo_response = requests.get(cls.GOOGLE_USERINFO_URL, headers=headers)
            logger.info(
                f"Google userinfo response status: {userinfo_response.status_code}"
            )

            if not userinfo_response.ok:
                logger.error(
                    f"Google userinfo request failed: {userinfo_response.status_code} - {userinfo_response.text}"
                )
                userinfo_response.raise_for_status()

            user_info = userinfo_response.json()
            logger.info(f"Received user info: {user_info}")

            # Extract required fields
            email = user_info.get("email")
            oauth_id = user_info.get("id")
            name = user_info.get("name", "")

            if not email or not oauth_id:
                logger.error(
                    f"Missing required fields in user info: email={email}, oauth_id={oauth_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid user info from Google",
                )

            logger.info(
                f"Successfully extracted user info: email={email}, oauth_id={oauth_id}"
            )
            return {
                "email": email,
                "oauth_id": oauth_id,
                "name": name,
                "verified": user_info.get("verified_email", False),
            }

        except requests.RequestException as e:
            logger.error(f"Request exception during Google OAuth: {e!s}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to communicate with Google: {e!s}",
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error during Google OAuth: {e!s}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error during Google OAuth: {e!s}",
            ) from e

    @classmethod
    def authenticate_user(cls, db: Session, code: str) -> dict[str, Any]:
        """Authenticate user with Google OAuth code"""
        try:
            logger.info("Starting Google OAuth authentication process")

            # Get user info from Google
            logger.info("Getting user info from Google")
            google_user_info = cls.get_google_user_info(code)
            logger.info(f"Google user info received: {google_user_info}")

            # Create or get user from database
            logger.info("Creating or getting OAuth user from database")
            user = create_or_get_oauth_user(
                db=db,
                email=google_user_info["email"],
                oauth_provider="google",
                oauth_id=google_user_info["oauth_id"],
                username=google_user_info["name"] if google_user_info["name"] else None,
            )
            logger.info(f"User created/retrieved: {user.id} - {user.email}")

            # Create access token
            logger.info("Creating access token")
            access_token = create_access_token(data={"sub": user.email})
            logger.info("Access token created successfully")

            result = {
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "verified": user.verified,
                    "has_password": bool(user.password_hash),
                    "created_at": user.created_at,
                    "updated_at": user.updated_at,
                },
            }

            logger.info(
                f"OAuth authentication completed successfully for user: {user.email}"
            )
            return result

        except Exception as e:
            logger.error(f"Error in authenticate_user: {e!s}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Authentication failed: {e!s}",
            ) from e
