# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Linear OAuth Manager

Handles OAuth 2.0 client credentials flow for Linear API authentication.
Manages token lifecycle including acquisition, caching, and refresh.
"""
import os
import requests
import logging
import time
from typing import Dict, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from dotenv import load_dotenv

from exceptions import LinearConfigError, LinearAuthError

load_dotenv()

# Configure logging
logger = logging.getLogger("linear.oauth")
logger.setLevel(logging.INFO)

class OAuthToken(BaseModel):
    """
    OAuth 2.0 access token with expiration tracking.
    
    Attributes:
        access_token: Bearer token for API authentication
        token_type: Token type (typically "Bearer")
        expires_in: Token lifetime in seconds
        scope: Granted OAuth scopes
        created_at: Token creation timestamp
    """
    access_token: str
    token_type: str
    expires_in: int
    scope: str
    created_at: datetime

    @property
    def expires_at(self) -> datetime:
        """Calculate token expiration time."""
        return self.created_at + timedelta(seconds=self.expires_in)

    @property
    def is_expired(self) -> bool:
        """Check if token has expired."""
        return datetime.now() >= self.expires_at

    @property
    def needs_refresh(self) -> bool:
        """Check if token should be refreshed (< 5 minutes remaining)."""
        return datetime.now() >= (self.expires_at - timedelta(minutes=5))

class LinearOAuthManager:
    """
    Manages OAuth 2.0 authentication for Linear API.
    
    Handles client credentials flow with automatic token refresh
    and retry logic for transient failures.
    """
    
    def __init__(self) -> None:
        """
        Initialize OAuth manager with credentials from environment.
        
        Raises:
            LinearConfigError: If LINEAR_CLIENT_ID or LINEAR_CLIENT_SECRET missing
        """
        self.client_id = os.getenv("LINEAR_CLIENT_ID")
        self.client_secret = os.getenv("LINEAR_CLIENT_SECRET")

        if not self.client_id or not self.client_secret:
            raise LinearConfigError(
                "LINEAR_CLIENT_ID and LINEAR_CLIENT_SECRET are required for OAuth"
            )

        self.token_url = "https://api.linear.app/oauth/token"
        self.current_token: Optional[OAuthToken] = None
        
        logger.info("LinearOAuthManager initialized")

    def get_client_credentials_token(self) -> OAuthToken:
        """
        Get an access token using client credentials flow.
        
        Implements automatic token caching and refresh. Retries on transient
        failures (502, 503, 504) with exponential backoff.
        
        Returns:
            Valid OAuth access token
            
        Raises:
            LinearAuthError: If token acquisition fails after retries
        """
        # Check if current token is still valid
        if self.current_token and not self.current_token.needs_refresh:
            logger.debug("Using cached OAuth token")
            return self.current_token

        logger.info("Requesting new OAuth token")

        # Request new token using client credentials
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "read write issues:create comments:create app:assignable app:mentionable"
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        # Retry logic for transient errors (502, 503, 504)
        max_retries = 3
        retry_delay = 1  # seconds

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.token_url,
                    data=payload,
                    headers=headers,
                    timeout=30
                )

                if response.status_code == 200:
                    break

                # Retry on server errors
                if response.status_code in [502, 503, 504] and attempt < max_retries - 1:
                    logger.warning(
                        f"OAuth request failed with {response.status_code}, "
                        f"retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue

                # Non-retryable error or last attempt
                error_msg = f"OAuth token request failed: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise LinearAuthError(error_msg)

            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"OAuth request error: {e}, "
                        f"retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                error_msg = f"OAuth token request failed after {max_retries} attempts: {e}"
                logger.error(error_msg)
                raise LinearAuthError(error_msg)

        token_data = response.json()

        # Create token object
        self.current_token = OAuthToken(
            access_token=token_data["access_token"],
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=token_data.get("expires_in", 86400),  # Default 24 hours
            scope=token_data.get("scope", ""),
            created_at=datetime.now()
        )

        logger.info(f"OAuth token acquired, expires in {self.current_token.expires_in}s")
        return self.current_token

    def get_access_token(self) -> str:
        """
        Get a valid access token, refreshing if necessary.
        
        Returns:
            Bearer token string
            
        Raises:
            LinearAuthError: If token acquisition fails
        """
        token = self.get_client_credentials_token()
        return token.access_token

    def get_authorization_headers(self) -> Dict[str, str]:
        """
        Get HTTP headers with valid authorization token.
        
        Returns:
            Dictionary with Authorization and Content-Type headers
            
        Raises:
            LinearAuthError: If token acquisition fails
        """
        token = self.get_client_credentials_token()

        return {
            "Authorization": f"Bearer {token.access_token}",
            "Content-Type": "application/json"
        }

    def validate_token(self) -> bool:
        """
        Validate current token by making a test API call.
        
        Returns:
            True if token is valid, False otherwise
        """
        try:
            headers = self.get_authorization_headers()

            # Test with a simple query
            test_query = """
            query TestAuth {
                viewer {
                    id
                    name
                }
            }
            """

            response = requests.post(
                "https://api.linear.app/graphql",
                json={"query": test_query},
                headers=headers,
                timeout=10
            )

            is_valid = response.status_code == 200 and "errors" not in response.json()
            
            if is_valid:
                logger.debug("Token validation successful")
            else:
                logger.warning("Token validation failed")
                
            return is_valid

        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return False
