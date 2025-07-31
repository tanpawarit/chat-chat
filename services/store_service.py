"""
Store service for managing store configurations and operations.
"""

from pathlib import Path
from typing import Any

import yaml

from models.platform import AdapterCapabilities
from models.store import Store, StorePlatformConfig


class StoreService:
    """Service for managing store configurations."""

    def __init__(self, config_path: str | Path | None = None):
        """
        Initialize store service.

        Args:
            config_path: Path to config.yaml file. If None, uses default path.
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"

        self.config_path = Path(config_path)
        self._stores: dict[str, Store] = {}
        self._load_stores()

    def _load_stores(self) -> None:
        """Load stores from config.yaml file."""
        try:
            with open(self.config_path, encoding="utf-8") as file:
                config = yaml.safe_load(file)

            stores_config = config.get("stores", {})
            self._stores = {}

            for store_id, store_data in stores_config.items():
                platforms = {}

                # Parse platform configurations
                for platform_name, platform_config in store_data.get(
                    "platforms", {}
                ).items():
                    if isinstance(platform_config, dict):
                        # Parse capabilities if present
                        capabilities = None
                        if "capabilities" in platform_config:
                            capabilities = AdapterCapabilities(
                                **platform_config["capabilities"]
                            )

                        platforms[platform_name] = StorePlatformConfig(
                            enabled=platform_config.get("enabled", False),
                            channel_secret=platform_config.get("channel_secret"),
                            channel_access_token=platform_config.get(
                                "channel_access_token"
                            ),
                            capabilities=capabilities,
                            platform_data=platform_config.get("platform_data", {}),
                        )

                # Create store object
                store = Store(
                    store_id=store_id,
                    name=store_data.get("name", store_id),
                    active=store_data.get("active", True),
                    platforms=platforms,
                    metadata=store_data.get("metadata", {}),
                )

                self._stores[store_id] = store

        except FileNotFoundError:
            print(f"Config file not found: {self.config_path}")
            self._stores = {}
        except yaml.YAMLError as e:
            print(f"Error parsing config file: {e}")
            self._stores = {}
        except Exception as e:
            print(f"Error loading stores: {e}")
            self._stores = {}

    def get_store(self, store_id: str) -> Store | None:
        """
        Get store by ID.

        Args:
            store_id: Store identifier

        Returns:
            Store object if found and active, None otherwise
        """
        store = self._stores.get(store_id)
        if store and store.active:
            return store
        return None

    def get_all_stores(self) -> dict[str, Store]:
        """
        Get all active stores.

        Returns:
            Dictionary of store_id -> Store for all active stores
        """
        return {
            store_id: store for store_id, store in self._stores.items() if store.active
        }

    def get_store_platform_config(
        self, store_id: str, platform: str
    ) -> StorePlatformConfig | None:
        """
        Get platform configuration for a specific store.

        Args:
            store_id: Store identifier
            platform: Platform name (line, facebook, etc.)

        Returns:
            StorePlatformConfig if found and enabled, None otherwise
        """
        store = self.get_store(store_id)
        if store:
            return store.get_platform_config(platform)
        return None

    def is_store_platform_enabled(self, store_id: str, platform: str) -> bool:
        """
        Check if a platform is enabled for a specific store.

        Args:
            store_id: Store identifier
            platform: Platform name

        Returns:
            True if platform is enabled for the store, False otherwise
        """
        store = self.get_store(store_id)
        if store:
            return store.is_platform_enabled(platform)
        return False

    def list_stores_by_platform(self, platform: str) -> list[Store]:
        """
        Get all stores that have a specific platform enabled.

        Args:
            platform: Platform name

        Returns:
            List of stores with the platform enabled
        """
        return [
            store
            for store in self._stores.values()
            if store.active and store.is_platform_enabled(platform)
        ]

    def reload_config(self) -> None:
        """Reload store configurations from config file."""
        self._load_stores()

    def get_store_count(self) -> int:
        """
        Get total number of active stores.

        Returns:
            Number of active stores
        """
        return len([store for store in self._stores.values() if store.active])

    def validate_store_config(self, store_id: str) -> dict[str, Any]:
        """
        Validate store configuration.

        Args:
            store_id: Store identifier

        Returns:
            Dictionary with validation results
        """
        store = self._stores.get(store_id)
        if not store:
            return {"valid": False, "errors": [f"Store {store_id} not found"]}

        errors = []
        warnings = []

        # Check if store is active
        if not store.active:
            warnings.append(f"Store {store_id} is inactive")

        # Validate platform configurations
        for platform_name, platform_config in store.platforms.items():
            if platform_config.enabled and platform_name == "line":
                if not platform_config.channel_secret:
                    errors.append(f"LINE channel_secret missing for store {store_id}")
                if not platform_config.channel_access_token:
                    errors.append(
                        f"LINE channel_access_token missing for store {store_id}"
                    )

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}
