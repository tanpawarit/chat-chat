"""
Customer service for managing customer data and operations.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from models.customer import Customer, CustomerStats
from models.platform import PlatformType
from models.user import UserProfile


class CustomerService:
    """Service for managing customer data."""

    def __init__(self, data_path: str | Path | None = None):
        """
        Initialize customer service.

        Args:
            data_path: Path to customer data directory. If None, uses default path.
        """
        if data_path is None:
            data_path = Path(__file__).parent.parent / "data"

        self.data_path = Path(data_path)
        self.customers_file = self.data_path / "customers.json"

        # Create data directory if it doesn't exist
        self.data_path.mkdir(exist_ok=True)

        # Initialize customers data structure
        self._customers: dict[str, dict[str, dict[str, Any]]] = {}
        self._load_customers()

    def _load_customers(self) -> None:
        """Load customers from JSON file."""
        try:
            if self.customers_file.exists():
                with open(self.customers_file, encoding="utf-8") as file:
                    self._customers = json.load(file)
            else:
                self._customers = {}
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error loading customers data: {e}")
            self._customers = {}

    def _save_customers(self) -> None:
        """Save customers to JSON file."""
        try:
            with open(self.customers_file, "w", encoding="utf-8") as file:
                json.dump(
                    self._customers, file, indent=2, default=str, ensure_ascii=False
                )
        except Exception as e:
            print(f"Error saving customers data: {e}")

    def get_customer(
        self, store_id: str, platform: str, platform_user_id: str
    ) -> Customer | None:
        """
        Get customer by store, platform, and platform user ID.

        Args:
            store_id: Store identifier
            platform: Platform name
            platform_user_id: Platform-specific user ID

        Returns:
            Customer object if found, None otherwise
        """
        store_customers = self._customers.get(store_id, {})
        customer_key = f"{platform}_{platform_user_id}"
        customer_data = store_customers.get(customer_key)

        if customer_data:
            try:
                # Parse profile if present
                profile = None
                if customer_data.get("profile"):
                    profile = UserProfile(**customer_data["profile"])

                return Customer(
                    customer_id=customer_data["customer_id"],
                    store_id=customer_data["store_id"],
                    platform=PlatformType(customer_data["platform"]),
                    platform_user_id=customer_data["platform_user_id"],
                    profile=profile,
                    created_at=datetime.fromisoformat(customer_data["created_at"]),
                    last_seen=datetime.fromisoformat(customer_data["last_seen"]),
                    message_count=customer_data.get("message_count", 0),
                    preferences=customer_data.get("preferences", {}),
                    metadata=customer_data.get("metadata", {}),
                )
            except Exception as e:
                print(f"Error parsing customer data: {e}")
                return None

        return None

    def create_customer(
        self,
        store_id: str,
        platform: PlatformType,
        platform_user_id: str,
        profile: UserProfile | None = None,
    ) -> Customer:
        """
        Create a new customer.

        Args:
            store_id: Store identifier
            platform: Platform type
            platform_user_id: Platform-specific user ID
            profile: User profile data

        Returns:
            Created Customer object
        """
        customer_id = Customer.generate_customer_id(
            store_id, platform.value, platform_user_id
        )

        customer = Customer(
            customer_id=customer_id,
            store_id=store_id,
            platform=platform,
            platform_user_id=platform_user_id,
            profile=profile,
            created_at=datetime.utcnow(),
            last_seen=datetime.utcnow(),
            message_count=0,
            preferences={},
            metadata={},
        )

        self.save_customer(customer)
        return customer

    def save_customer(self, customer: Customer) -> None:
        """
        Save customer to storage.

        Args:
            customer: Customer object to save
        """
        if customer.store_id not in self._customers:
            self._customers[customer.store_id] = {}

        customer_key = f"{customer.platform.value}_{customer.platform_user_id}"

        # Convert customer to dict for JSON storage
        customer_data = {
            "customer_id": customer.customer_id,
            "store_id": customer.store_id,
            "platform": customer.platform.value,
            "platform_user_id": customer.platform_user_id,
            "profile": customer.profile.dict() if customer.profile else None,
            "created_at": customer.created_at.isoformat(),
            "last_seen": customer.last_seen.isoformat(),
            "message_count": customer.message_count,
            "preferences": customer.preferences,
            "metadata": customer.metadata,
        }

        self._customers[customer.store_id][customer_key] = customer_data
        self._save_customers()

    def get_or_create_customer(
        self,
        store_id: str,
        platform: PlatformType,
        platform_user_id: str,
        profile: UserProfile | None = None,
    ) -> Customer:
        """
        Get existing customer or create new one if not found.

        Args:
            store_id: Store identifier
            platform: Platform type
            platform_user_id: Platform-specific user ID
            profile: User profile data (used only when creating new customer)

        Returns:
            Customer object (existing or newly created)
        """
        customer = self.get_customer(store_id, platform.value, platform_user_id)

        if customer:
            # Update last_seen timestamp
            customer.last_seen = datetime.utcnow()
            self.save_customer(customer)
            return customer
        else:
            # Create new customer
            return self.create_customer(store_id, platform, platform_user_id, profile)

    def update_customer_profile(
        self, customer: Customer, profile: UserProfile
    ) -> Customer:
        """
        Update customer profile.

        Args:
            customer: Customer to update
            profile: New profile data

        Returns:
            Updated customer object
        """
        customer.profile = profile
        customer.last_seen = datetime.utcnow()
        self.save_customer(customer)
        return customer

    def increment_message_count(self, customer: Customer) -> Customer:
        """
        Increment customer message count.

        Args:
            customer: Customer to update

        Returns:
            Updated customer object
        """
        customer.increment_message_count()
        self.save_customer(customer)
        return customer

    def get_store_customers(self, store_id: str) -> list[Customer]:
        """
        Get all customers for a store.

        Args:
            store_id: Store identifier

        Returns:
            List of customers for the store
        """
        customers = []
        store_customers = self._customers.get(store_id, {})

        for customer_data in store_customers.values():
            try:
                profile = None
                if customer_data.get("profile"):
                    profile = UserProfile(**customer_data["profile"])

                customer = Customer(
                    customer_id=customer_data["customer_id"],
                    store_id=customer_data["store_id"],
                    platform=PlatformType(customer_data["platform"]),
                    platform_user_id=customer_data["platform_user_id"],
                    profile=profile,
                    created_at=datetime.fromisoformat(customer_data["created_at"]),
                    last_seen=datetime.fromisoformat(customer_data["last_seen"]),
                    message_count=customer_data.get("message_count", 0),
                    preferences=customer_data.get("preferences", {}),
                    metadata=customer_data.get("metadata", {}),
                )
                customers.append(customer)
            except Exception as e:
                print(f"Error parsing customer data: {e}")
                continue

        return customers

    def get_customer_stats(self, store_id: str) -> CustomerStats:
        """
        Get customer statistics for a store.

        Args:
            store_id: Store identifier

        Returns:
            CustomerStats object
        """
        customers = self.get_store_customers(store_id)

        # Calculate statistics
        total_customers = len(customers)

        # Active customers (messaged in last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        active_customers = len([c for c in customers if c.last_seen >= thirty_days_ago])

        # New customers today
        today = datetime.utcnow().date()
        new_customers_today = len(
            [c for c in customers if c.created_at.date() == today]
        )

        # Platform breakdown
        platform_breakdown = {}
        for customer in customers:
            platform = customer.platform.value
            platform_breakdown[platform] = platform_breakdown.get(platform, 0) + 1

        return CustomerStats(
            store_id=store_id,
            total_customers=total_customers,
            active_customers=active_customers,
            new_customers_today=new_customers_today,
            platform_breakdown=platform_breakdown,
        )

    def delete_customer(
        self, store_id: str, platform: str, platform_user_id: str
    ) -> bool:
        """
        Delete a customer.

        Args:
            store_id: Store identifier
            platform: Platform name
            platform_user_id: Platform-specific user ID

        Returns:
            True if customer was deleted, False if not found
        """
        store_customers = self._customers.get(store_id, {})
        customer_key = f"{platform}_{platform_user_id}"

        if customer_key in store_customers:
            del store_customers[customer_key]
            self._save_customers()
            return True

        return False

    def get_total_customers(self) -> int:
        """
        Get total number of customers across all stores.

        Returns:
            Total customer count
        """
        total = 0
        for store_customers in self._customers.values():
            total += len(store_customers)
        return total
