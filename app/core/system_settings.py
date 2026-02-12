"""System settings manager - loads configuration from database."""
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import SystemSettings

logger = logging.getLogger(__name__)


class SystemSettingsManager:
    """Manager for system settings stored in database."""

    # Settings that can be loaded from database
    # (DATABASE_URL always comes from env/secret to avoid circular dependency)
    DB_OVERRIDABLE_SETTINGS = {
        # API Keys
        "openai_api_key": "OPENAI_API_KEY",
        "voyage_api_key": "VOYAGE_API_KEY",
        "anthropic_api_key": "ANTHROPIC_API_KEY",
        "deepseek_api_key": "DEEPSEEK_API_KEY",
        "ollama_base_url": "OLLAMA_BASE_URL",
        "mcp_enabled": "MCP_ENABLED",
        "mcp_path": "MCP_PATH",
        "mcp_public_base_url": "MCP_PUBLIC_BASE_URL",
        "mcp_default_kb_id": "MCP_DEFAULT_KB_ID",
        "mcp_tools_enabled": "MCP_TOOLS_ENABLED",
        "mcp_auth_mode": "MCP_AUTH_MODE",
        "mcp_access_token_ttl_minutes": "MCP_ACCESS_TOKEN_TTL_MINUTES",
        "mcp_refresh_token_ttl_days": "MCP_REFRESH_TOKEN_TTL_DAYS",

        # Database URLs
        "qdrant_url": "QDRANT_URL",
        "qdrant_api_key": "QDRANT_API_KEY",
        "opensearch_url": "OPENSEARCH_URL",
        "opensearch_username": "OPENSEARCH_USERNAME",
        "opensearch_password": "OPENSEARCH_PASSWORD",

        # System settings
        "system_name": "SYSTEM_NAME",
        "max_file_size_mb": "MAX_FILE_SIZE_MB",
        "max_chunk_size": "MAX_CHUNK_SIZE",
        "chunk_overlap": "CHUNK_OVERLAP",
    }

    @staticmethod
    async def load_from_db(db: AsyncSession) -> Dict[str, Any]:
        """
        Load all system settings from database.

        Args:
            db: Database session

        Returns:
            Dictionary of settings (DB key -> value)
        """
        try:
            result = await db.execute(
                select(SystemSettings)
            )
            settings = result.scalars().all()

            settings_dict = {}
            for setting in settings:
                # For now, we don't decrypt (no encryption in MVP)
                settings_dict[setting.key] = setting.value

            logger.info(f"Loaded {len(settings_dict)} settings from database")
            return settings_dict

        except Exception as e:
            logger.warning(f"Failed to load settings from database: {e}")
            return {}

    @staticmethod
    async def is_setup_complete(db: AsyncSession) -> bool:
        """
        Check if initial setup has been completed.

        Setup is considered complete if there are critical settings in database.

        Args:
            db: Database session

        Returns:
            True if setup is complete
        """
        try:
            # Check if at least one AI provider is configured
            result = await db.execute(
                select(SystemSettings).where(
                    SystemSettings.key.in_([
                        "openai_api_key",
                        "voyage_api_key",
                        "anthropic_api_key",
                        "deepseek_api_key",
                        "ollama_base_url",
                        "setup_completed"  # Explicit flag
                    ])
                )
            )
            settings = result.scalars().all()

            return len(settings) > 0

        except Exception as e:
            logger.warning(f"Failed to check setup completion: {e}")
            # If can't check, assume setup is needed
            return False

    @staticmethod
    async def save_setting(
        db: AsyncSession,
        key: str,
        value: str,
        category: str,
        description: Optional[str] = None,
        is_encrypted: bool = False,
        updated_by: Optional[int] = None,
    ) -> SystemSettings:
        """
        Save or update a system setting.

        Args:
            db: Database session
            key: Setting key
            value: Setting value (plain text for now)
            category: Setting category (api, database, system, limits)
            description: Optional description
            is_encrypted: Whether value should be encrypted (for future)
            updated_by: Admin user ID who updated this setting

        Returns:
            Created or updated SystemSettings instance
        """
        if isinstance(value, str):
            value = value.strip()
        # Check if setting exists
        result = await db.execute(
            select(SystemSettings).where(SystemSettings.key == key)
        )
        setting = result.scalar_one_or_none()

        if setting:
            # Update existing
            setting.value = value
            setting.category = category
            setting.description = description
            setting.is_encrypted = is_encrypted
            setting.updated_by = updated_by
            setting.updated_at = datetime.utcnow()
        else:
            # Create new
            setting = SystemSettings(
                key=key,
                value=value,
                category=category,
                description=description,
                is_encrypted=is_encrypted,
                updated_by=updated_by,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(setting)

        await db.commit()
        await db.refresh(setting)

        logger.info(f"Saved setting '{key}' (category: {category})")
        return setting

    @staticmethod
    async def get_setting(db: AsyncSession, key: str) -> Optional[str]:
        """
        Get a single setting value.

        Args:
            db: Database session
            key: Setting key

        Returns:
            Setting value or None if not found
        """
        try:
            result = await db.execute(
                select(SystemSettings).where(SystemSettings.key == key)
            )
            setting = result.scalar_one_or_none()

            return setting.value if setting else None

        except Exception as e:
            logger.warning(f"Failed to get setting '{key}': {e}")
            return None

    @staticmethod
    async def ensure_defaults(db: AsyncSession, defaults: Dict[str, tuple[str, str, Optional[str]]]) -> None:
        """
        Ensure default settings exist in DB if missing.

        Args:
            db: Database session
            defaults: key -> (value, category, description)
        """
        if not defaults:
            return
        result = await db.execute(
            select(SystemSettings.key).where(SystemSettings.key.in_(list(defaults.keys())))
        )
        existing = {row[0] for row in result.all()}
        for key, (value, category, description) in defaults.items():
            if key in existing:
                continue
            await SystemSettingsManager.save_setting(
                db=db,
                key=key,
                value=value,
                category=category,
                description=description,
                is_encrypted=False,
            )

    @staticmethod
    async def delete_setting(db: AsyncSession, key: str) -> bool:
        """
        Delete a system setting.

        Args:
            db: Database session
            key: Setting key

        Returns:
            True if deleted, False if not found
        """
        try:
            result = await db.execute(
                select(SystemSettings).where(SystemSettings.key == key)
            )
            setting = result.scalar_one_or_none()

            if setting:
                await db.delete(setting)
                await db.commit()
                logger.info(f"Deleted setting '{key}'")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to delete setting '{key}': {e}")
            return False

    @staticmethod
    def merge_with_env_settings(
        db_settings: Dict[str, Any],
        env_settings: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Merge database settings with environment settings.

        Priority: DB > ENV > Defaults

        Args:
            db_settings: Settings from database (DB keys)
            env_settings: Settings from environment (ENV variable names)

        Returns:
            Merged settings dictionary (ENV variable names)
        """
        merged = env_settings.copy()

        # Override with DB settings
        for db_key, env_key in SystemSettingsManager.DB_OVERRIDABLE_SETTINGS.items():
            if db_key in db_settings and db_settings[db_key]:
                value = db_settings[db_key]
                if isinstance(value, str):
                    value = value.strip()
                merged[env_key] = value
                logger.debug(f"Overriding {env_key} from database")

        return merged
