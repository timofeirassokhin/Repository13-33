from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

import google.auth.transport.requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from src.db.repositories.user_repo import UserRepository
from src.services.base import BaseService

if TYPE_CHECKING:
    from src.config import Settings
    from src.db.connection import Database

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    pass


class GoogleAuthService(BaseService):
    def __init__(self, db: Database, settings: Settings) -> None:
        super().__init__(db, settings)
        self._user_repo = UserRepository(db)

    def _get_client_config(self) -> dict[str, Any]:
        return {
            "web": {
                "client_id": self._settings.google_client_id,
                "client_secret": self._settings.google_client_secret.get_secret_value(),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self._settings.google_redirect_uri],
            }
        }

    def get_auth_url(self, telegram_user_id: int) -> str:
        flow = Flow.from_client_config(
            client_config=self._get_client_config(),
            scopes=self._settings.google_scopes,
            redirect_uri=self._settings.google_redirect_uri,
        )
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            prompt="consent",
            state=str(telegram_user_id),
        )
        return auth_url

    async def handle_callback(self, code: str, state: str) -> None:
        telegram_user_id = int(state)
        flow = Flow.from_client_config(
            client_config=self._get_client_config(),
            scopes=self._settings.google_scopes,
            redirect_uri=self._settings.google_redirect_uri,
        )
        await asyncio.to_thread(flow.fetch_token, code=code)
        creds = flow.credentials
        await self._user_repo.upsert_tokens(
            telegram_user_id=telegram_user_id,
            access_token=creds.token,
            refresh_token=creds.refresh_token,
            expiry=creds.expiry.isoformat() if creds.expiry else "",
        )
        logger.info("OAuth callback handled for user %d", telegram_user_id)

    async def get_credentials(self, telegram_user_id: int) -> Credentials:
        user = await self._user_repo.get_user(telegram_user_id)
        if not user or not user["google_refresh_token"]:
            raise AuthenticationError("User not authenticated with Google")

        creds = Credentials(
            token=user["google_access_token"],
            refresh_token=user["google_refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self._settings.google_client_id,
            client_secret=self._settings.google_client_secret.get_secret_value(),
        )

        if creds.expired and creds.refresh_token:
            request = google.auth.transport.requests.Request()
            await asyncio.to_thread(creds.refresh, request)
            await self._user_repo.upsert_tokens(
                telegram_user_id=telegram_user_id,
                access_token=creds.token,
                refresh_token=creds.refresh_token,
                expiry=creds.expiry.isoformat() if creds.expiry else "",
            )
            logger.info("Tokens refreshed for user %d", telegram_user_id)

        return creds

    async def build_service(
        self, api_name: str, api_version: str, telegram_user_id: int
    ) -> Any:
        creds = await self.get_credentials(telegram_user_id)
        return await asyncio.to_thread(
            build, api_name, api_version, credentials=creds
        )

    async def revoke(self, telegram_user_id: int) -> None:
        await self._user_repo.delete_user(telegram_user_id)
        logger.info("Credentials revoked for user %d", telegram_user_id)
