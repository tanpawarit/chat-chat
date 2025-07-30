"""
Adapter factory for creating platform adapters dynamically based on store configuration.
"""

from typing import Any

from adapters.base.platform_base import PlatformAdapter
from adapters.platforms.line_adapter import LineAdapter
from models.platform import LineConfig, PlatformType
from models.store import Store


class AdapterFactory:
    """Factory for creating platform adapters for stores."""

    def __init__(self):
        """Initialize adapter factory."""
        self._adapters: dict[str, dict[str, PlatformAdapter]] = {}

    def create_line_adapter(self, store: Store) -> LineAdapter | None:
        """
        Create LINE adapter for a store.

        Args:
            store: Store configuration

        Returns:
            LineAdapter if configuration is valid, None otherwise
        """
        platform_config = store.get_platform_config("line")
        if not platform_config:
            return None

        if (
            not platform_config.channel_secret
            or not platform_config.channel_access_token
        ):
            print(f"Missing LINE credentials for store {store.store_id}")
            return None

        try:
            line_config = LineConfig(
                platform=PlatformType.LINE,
                channel_secret=platform_config.channel_secret,
                channel_access_token=platform_config.channel_access_token,
                capabilities=platform_config.capabilities,
            )

            return LineAdapter(line_config)

        except Exception as e:
            print(f"Error creating LINE adapter for store {store.store_id}: {e}")
            return None

    def get_adapter(
        self, store_id: str, platform: str, store: Store
    ) -> PlatformAdapter | None:
        """
        Get or create adapter for store and platform.

        Args:
            store_id: Store identifier
            platform: Platform name (line, facebook, etc.)
            store: Store configuration

        Returns:
            PlatformAdapter if available, None otherwise
        """
        # Check if adapter already exists in cache
        if store_id in self._adapters and platform in self._adapters[store_id]:
            return self._adapters[store_id][platform]

        # Create new adapter
        adapter = None

        if platform == "line":
            adapter = self.create_line_adapter(store)
        # Add other platforms here:
        # elif platform == "facebook":
        #     adapter = self.create_facebook_adapter(store)
        # elif platform == "telegram":
        #     adapter = self.create_telegram_adapter(store)

        # Cache the adapter if created successfully
        if adapter:
            if store_id not in self._adapters:
                self._adapters[store_id] = {}
            self._adapters[store_id][platform] = adapter

        return adapter

    def get_all_adapters_for_store(self, store: Store) -> dict[str, PlatformAdapter]:
        """
        Get all adapters for a store (for all enabled platforms).

        Args:
            store: Store configuration

        Returns:
            Dictionary of platform -> adapter for all enabled platforms
        """
        adapters = {}

        for platform_name, platform_config in store.platforms.items():
            if platform_config.enabled:
                adapter = self.get_adapter(store.store_id, platform_name, store)
                if adapter:
                    adapters[platform_name] = adapter

        return adapters

    def remove_adapter(self, store_id: str, platform: str) -> None:
        """
        Remove adapter from cache.

        Args:
            store_id: Store identifier
            platform: Platform name
        """
        if store_id in self._adapters and platform in self._adapters[store_id]:
            del self._adapters[store_id][platform]

            # Clean up empty store entry
            if not self._adapters[store_id]:
                del self._adapters[store_id]

    def clear_store_adapters(self, store_id: str) -> None:
        """
        Clear all adapters for a store.

        Args:
            store_id: Store identifier
        """
        if store_id in self._adapters:
            del self._adapters[store_id]

    def clear_all_adapters(self) -> None:
        """Clear all cached adapters."""
        self._adapters.clear()

    def get_cached_adapter_count(self) -> int:
        """
        Get total number of cached adapters.

        Returns:
            Number of cached adapters
        """
        count = 0
        for store_adapters in self._adapters.values():
            count += len(store_adapters)
        return count

    def get_store_adapter_count(self, store_id: str) -> int:
        """
        Get number of adapters for a specific store.

        Args:
            store_id: Store identifier

        Returns:
            Number of adapters for the store
        """
        if store_id in self._adapters:
            return len(self._adapters[store_id])
        return 0

    def validate_store_adapters(self, store: Store) -> dict[str, Any]:
        """
        Validate that adapters can be created for all enabled platforms in a store.

        Args:
            store: Store configuration

        Returns:
            Dictionary with validation results
        """
        results = {
            "store_id": store.store_id,
            "valid": True,
            "platforms": {},
            "errors": [],
        }

        for platform_name, platform_config in store.platforms.items():
            if platform_config.enabled:
                try:
                    adapter = self.get_adapter(store.store_id, platform_name, store)
                    if adapter:
                        results["platforms"][platform_name] = {
                            "status": "valid",
                            "adapter_type": type(adapter).__name__,
                        }
                    else:
                        results["platforms"][platform_name] = {
                            "status": "failed",
                            "error": "Could not create adapter",
                        }
                        results["valid"] = False
                        results["errors"].append(
                            f"Failed to create {platform_name} adapter"
                        )

                except Exception as e:
                    results["platforms"][platform_name] = {
                        "status": "error",
                        "error": str(e),
                    }
                    results["valid"] = False
                    results["errors"].append(
                        f"Error creating {platform_name} adapter: {e}"
                    )

        return results
