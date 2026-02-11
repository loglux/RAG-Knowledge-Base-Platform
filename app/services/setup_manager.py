"""Setup wizard business logic."""
import logging
import secrets
import string
from typing import Optional, Dict, Any
from datetime import datetime

import bcrypt
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import AdminUser, SystemSettings
from app.core.system_settings import SystemSettingsManager

logger = logging.getLogger(__name__)


class SetupError(Exception):
    """Base exception for setup errors."""
    pass


class SetupAlreadyCompleteError(SetupError):
    """Raised when trying to run setup but it's already complete."""
    pass


class SetupManager:
    """Manager for system setup wizard."""

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Bcrypt password hash
        """
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """
        Verify password against hash.

        Args:
            password: Plain text password
            password_hash: Bcrypt hash

        Returns:
            True if password matches
        """
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

    @staticmethod
    async def create_admin_user(
        db: AsyncSession,
        username: str,
        password: str,
        email: Optional[str] = None,
    ) -> AdminUser:
        """
        Create initial admin user.

        Args:
            db: Database session
            username: Admin username
            password: Plain text password
            email: Optional email

        Returns:
            Created AdminUser instance

        Raises:
            SetupError: If admin already exists or creation fails
        """
        try:
            # Check if admin already exists
            result = await db.execute(
                select(AdminUser).where(AdminUser.username == username)
            )
            existing = result.scalar_one_or_none()

            if existing:
                raise SetupError(f"Admin user '{username}' already exists")

            # Hash password
            password_hash = SetupManager.hash_password(password)

            # Create admin
            admin = AdminUser(
                username=username,
                password_hash=password_hash,
                email=email,
                role="admin",
                is_active=True,
                created_at=datetime.utcnow(),
            )

            db.add(admin)
            await db.commit()
            await db.refresh(admin)

            logger.info(f"Created admin user: {username}")
            return admin

        except SetupError:
            await db.rollback()
            raise
        except Exception as e:
            logger.error(f"Failed to create admin user: {e}")
            await db.rollback()
            raise SetupError(f"Failed to create admin user: {e}") from e

    @staticmethod
    async def save_api_keys(
        db: AsyncSession,
        openai_api_key: Optional[str] = None,
        voyage_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        deepseek_api_key: Optional[str] = None,
        ollama_base_url: Optional[str] = None,
        updated_by: Optional[int] = None,
    ) -> None:
        """
        Save API keys to system settings.

        Args:
            db: Database session
            openai_api_key: OpenAI API key (optional)
            voyage_api_key: VoyageAI API key (optional)
            anthropic_api_key: Anthropic API key (optional)
            deepseek_api_key: DeepSeek API key (optional)
            ollama_base_url: Ollama API base URL (optional)
            updated_by: Admin user ID

        Raises:
            SetupError: If save fails
        """
        try:
            # Save OpenAI key
            if openai_api_key:
                await SystemSettingsManager.save_setting(
                    db=db,
                    key="openai_api_key",
                    value=openai_api_key,
                    category="api",
                    description="OpenAI API key for embeddings and chat",
                    is_encrypted=False,  # No encryption in MVP
                    updated_by=updated_by,
                )

            # Save Voyage key
            if voyage_api_key:
                await SystemSettingsManager.save_setting(
                    db=db,
                    key="voyage_api_key",
                    value=voyage_api_key,
                    category="api",
                    description="VoyageAI API key for embeddings",
                    is_encrypted=False,
                    updated_by=updated_by,
                )

            # Save Anthropic key
            if anthropic_api_key:
                await SystemSettingsManager.save_setting(
                    db=db,
                    key="anthropic_api_key",
                    value=anthropic_api_key,
                    category="api",
                    description="Anthropic API key for Claude models",
                    is_encrypted=False,
                    updated_by=updated_by,
                )

            # Save DeepSeek key
            if deepseek_api_key:
                await SystemSettingsManager.save_setting(
                    db=db,
                    key="deepseek_api_key",
                    value=deepseek_api_key,
                    category="api",
                    description="DeepSeek API key",
                    is_encrypted=False,
                    updated_by=updated_by,
                )

            # Save Ollama base URL
            if ollama_base_url:
                await SystemSettingsManager.save_setting(
                    db=db,
                    key="ollama_base_url",
                    value=ollama_base_url,
                    category="api",
                    description="Ollama API base URL for local LLM",
                    is_encrypted=False,
                    updated_by=updated_by,
                )

            logger.info("Saved API keys to system settings")

        except Exception as e:
            logger.exception(f"Failed to save API keys: {e}")  # Changed to .exception to include traceback
            raise SetupError(f"Failed to save API keys: {e}") from e

    @staticmethod
    async def save_database_settings(
        db: AsyncSession,
        qdrant_url: Optional[str] = None,
        qdrant_api_key: Optional[str] = None,
        opensearch_url: Optional[str] = None,
        opensearch_username: Optional[str] = None,
        opensearch_password: Optional[str] = None,
        updated_by: Optional[int] = None,
    ) -> None:
        """
        Save database connection settings.

        Args:
            db: Database session
            qdrant_url: Qdrant HTTP URL
            qdrant_api_key: Qdrant API key (optional)
            opensearch_url: OpenSearch HTTP URL
            opensearch_username: OpenSearch username (optional)
            opensearch_password: OpenSearch password (optional)
            updated_by: Admin user ID

        Raises:
            SetupError: If save fails
        """
        try:
            if qdrant_url:
                await SystemSettingsManager.save_setting(
                    db=db,
                    key="qdrant_url",
                    value=qdrant_url,
                    category="database",
                    description="Qdrant vector database HTTP URL",
                    is_encrypted=False,
                    updated_by=updated_by,
                )

            if qdrant_api_key:
                await SystemSettingsManager.save_setting(
                    db=db,
                    key="qdrant_api_key",
                    value=qdrant_api_key,
                    category="database",
                    description="Qdrant API key",
                    is_encrypted=False,
                    updated_by=updated_by,
                )

            if opensearch_url:
                await SystemSettingsManager.save_setting(
                    db=db,
                    key="opensearch_url",
                    value=opensearch_url,
                    category="database",
                    description="OpenSearch HTTP URL",
                    is_encrypted=False,
                    updated_by=updated_by,
                )

            if opensearch_username:
                await SystemSettingsManager.save_setting(
                    db=db,
                    key="opensearch_username",
                    value=opensearch_username,
                    category="database",
                    description="OpenSearch username",
                    is_encrypted=False,
                    updated_by=updated_by,
                )

            if opensearch_password:
                await SystemSettingsManager.save_setting(
                    db=db,
                    key="opensearch_password",
                    value=opensearch_password,
                    category="database",
                    description="OpenSearch password",
                    is_encrypted=False,
                    updated_by=updated_by,
                )

            logger.info("Saved database settings")

        except Exception as e:
            logger.error(f"Failed to save database settings: {e}")
            raise SetupError(f"Failed to save database settings: {e}") from e

    @staticmethod
    async def save_system_settings(
        db: AsyncSession,
        system_name: Optional[str] = None,
        max_file_size_mb: Optional[int] = None,
        max_chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        updated_by: Optional[int] = None,
    ) -> None:
        """
        Save general system settings.

        Args:
            db: Database session
            system_name: System name displayed in UI
            max_file_size_mb: Maximum file size in MB
            max_chunk_size: Maximum chunk size
            chunk_overlap: Chunk overlap size
            updated_by: Admin user ID

        Raises:
            SetupError: If save fails
        """
        try:
            if system_name:
                await SystemSettingsManager.save_setting(
                    db=db,
                    key="system_name",
                    value=system_name,
                    category="system",
                    description="System name displayed in UI",
                    is_encrypted=False,
                    updated_by=updated_by,
                )

            if max_file_size_mb is not None:
                await SystemSettingsManager.save_setting(
                    db=db,
                    key="max_file_size_mb",
                    value=str(max_file_size_mb),
                    category="limits",
                    description="Maximum file size in MB",
                    is_encrypted=False,
                    updated_by=updated_by,
                )

            if max_chunk_size is not None:
                await SystemSettingsManager.save_setting(
                    db=db,
                    key="max_chunk_size",
                    value=str(max_chunk_size),
                    category="system",
                    description="Maximum chunk size in characters",
                    is_encrypted=False,
                    updated_by=updated_by,
                )

            if chunk_overlap is not None:
                await SystemSettingsManager.save_setting(
                    db=db,
                    key="chunk_overlap",
                    value=str(chunk_overlap),
                    category="system",
                    description="Chunk overlap in characters",
                    is_encrypted=False,
                    updated_by=updated_by,
                )

            logger.info("Saved system settings")

        except Exception as e:
            logger.error(f"Failed to save system settings: {e}")
            raise SetupError(f"Failed to save system settings: {e}") from e

    @staticmethod
    async def mark_setup_complete(
        db: AsyncSession,
        updated_by: Optional[int] = None,
    ) -> None:
        """
        Mark setup as complete.

        Args:
            db: Database session
            updated_by: Admin user ID

        Raises:
            SetupError: If marking fails
        """
        try:
            await SystemSettingsManager.save_setting(
                db=db,
                key="setup_completed",
                value="true",
                category="system",
                description="Setup wizard completion flag",
                is_encrypted=False,
                updated_by=updated_by,
            )

            # Also save completion timestamp
            await SystemSettingsManager.save_setting(
                db=db,
                key="setup_completed_at",
                value=datetime.utcnow().isoformat(),
                category="system",
                description="Setup wizard completion timestamp",
                is_encrypted=False,
                updated_by=updated_by,
            )

            logger.info("Marked setup as complete")

        except Exception as e:
            logger.error(f"Failed to mark setup complete: {e}")
            raise SetupError(f"Failed to mark setup complete: {e}") from e

    @staticmethod
    async def get_setup_status(db: AsyncSession) -> Dict[str, Any]:
        """
        Get current setup status.

        Args:
            db: Database session

        Returns:
            Dictionary with setup status information
        """
        try:
            is_complete = await SystemSettingsManager.is_setup_complete(db)

            # Get admin users count
            result = await db.execute(select(AdminUser))
            admin_count = len(result.scalars().all())

            # Get settings count
            result = await db.execute(select(SystemSettings))
            settings_count = len(result.scalars().all())

            return {
                "is_complete": is_complete,
                "admin_users_count": admin_count,
                "settings_count": settings_count,
                "needs_setup": not is_complete,
            }

        except Exception as e:
            logger.error(f"Failed to get setup status: {e}")
            return {
                "is_complete": False,
                "admin_users_count": 0,
                "settings_count": 0,
                "needs_setup": True,
                "error": str(e),
            }

    @staticmethod
    def generate_secure_password(length: int = 24) -> str:
        """
        Generate cryptographically secure random password.

        Args:
            length: Password length (default 24)

        Returns:
            Random password string with mixed characters
        """
        # Character sets
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        special = "!@#$%^&*()-_=+[]{}|;:,.<>?"

        # Ensure at least one character from each set
        password = [
            secrets.choice(lowercase),
            secrets.choice(uppercase),
            secrets.choice(digits),
            secrets.choice(special),
        ]

        # Fill the rest with random characters from all sets
        all_chars = lowercase + uppercase + digits + special
        password.extend(secrets.choice(all_chars) for _ in range(length - 4))

        # Shuffle to avoid predictable pattern
        secrets.SystemRandom().shuffle(password)

        return ''.join(password)

    @staticmethod
    async def change_postgres_password(
        db: AsyncSession,
        username: str,
        new_password: str,
        updated_by: Optional[int] = None,
    ) -> Dict[str, str]:
        """
        Change PostgreSQL user password.

        Args:
            db: Database session
            username: PostgreSQL username
            new_password: New password
            updated_by: Admin user ID

        Returns:
            Dictionary with updated credentials

        Raises:
            SetupError: If password change fails
        """
        try:
            # Execute ALTER USER command
            # Escape single quotes in password by doubling them (SQL standard)
            escaped_password = new_password.replace("'", "''")
            alter_query = text(f"ALTER USER {username} WITH PASSWORD '{escaped_password}'")
            await db.execute(alter_query)
            await db.commit()

            # Get current DATABASE_URL from config
            from app.config import settings
            current_url = settings.DATABASE_URL

            # Parse current URL to replace password
            # Format: postgresql+asyncpg://user:pass@host:port/db
            if "@" in current_url:
                protocol_and_auth, host_and_db = current_url.split("@", 1)
                protocol, auth = protocol_and_auth.rsplit("//", 1)

                if ":" in auth:
                    db_username, _ = auth.split(":", 1)
                else:
                    db_username = auth

                # Construct new URL
                new_url = f"{protocol}//{db_username}:{new_password}@{host_and_db}"
            else:
                raise SetupError("Invalid DATABASE_URL format")

            logger.info(f"Changed PostgreSQL password for user: {username}")

            # CRITICAL: Recreate connection pool with new credentials
            # Without this, all new connections will fail with authentication error
            # because the pool still uses old password from environment variable
            from app.db.session import recreate_engine
            logger.info("Recreating database connection pool with new credentials...")
            await recreate_engine(new_url)

            return {
                "username": username,
                "password": new_password,
            }

        except Exception as e:
            logger.error(f"Failed to change PostgreSQL password: {e}")
            await db.rollback()
            raise SetupError(f"Failed to change PostgreSQL password: {e}") from e
