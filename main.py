"""
FastAPI application with multi-store webhook integration.
"""

import pprint

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from bot_gateway.gateway import BotGateway
from config.settings import load_config
from models.platform import PlatformType
from services.adapter_factory import AdapterFactory
from services.customer_service import CustomerService
from services.store_service import StoreService

# Initialize FastAPI app
app = FastAPI(
    title="Multi-Store Chat Bot",
    description="Multi-store, multi-platform chatbot with adapter architecture",
    version="2.0.0",
)

# Initialize services
store_service = StoreService()
customer_service = CustomerService()
adapter_factory = AdapterFactory()
gateway = BotGateway()

# Load configuration from config.yaml
config = load_config()


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Chat Chat Bot is running!", "status": "healthy"}


@app.get("/status")
async def get_status():
    """Get bot status with store information."""
    gateway_status = gateway.get_status()

    # Get store information
    stores = store_service.get_all_stores()
    store_info = {}

    for store_id, store in stores.items():
        enabled_platforms = []
        for platform_name, platform_config in store.platforms.items():
            if platform_config.enabled:
                enabled_platforms.append(
                    {
                        "platform": platform_name,
                        "webhook_path": f"/webhooks/{platform_name}/{store_id}",
                    }
                )

        store_info[store_id] = {
            "name": store.name,
            "active": store.active,
            "platforms": enabled_platforms,
        }

    return {
        "bot": gateway_status,
        "stores": store_info,
        "total_stores": store_service.get_store_count(),
        "total_customers": customer_service.get_total_customers(),
    }


@app.post("/webhooks/line")
async def line_webhook_legacy():
    """
    Legacy webhook endpoint - no longer supported.
    Returns explicit error directing to correct endpoint format.
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail={
            "error": "Legacy webhook endpoint no longer supported",
            "message": "Please use the store-specific webhook format: /webhooks/line/{store_id}",
            "examples": [
                "/webhooks/line/store_001",
                "/webhooks/line/store_002",
                "/webhooks/line/store_003",
            ],
            "documentation": "See store setup guide for proper webhook configuration",
        },
    )


@app.post("/webhooks/{platform}/{store_id}")
async def platform_webhook(platform: str, store_id: str, request: Request):
    """
    Dynamic webhook endpoint for any platform and store.

    Args:
        platform: Platform name (line, facebook, etc.)
        store_id: Store identifier
        request: HTTP request
    """
    try:
        print(f"Received webhook for platform: {platform}, store: {store_id}")

        # Get store configuration
        store = store_service.get_store(store_id)
        if not store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Store {store_id} not found or inactive",
            )

        # Check if platform is enabled for this store
        if not store.is_platform_enabled(platform):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Platform {platform} not enabled for store {store_id}",
            )

        # Get adapter for this store and platform
        adapter = adapter_factory.get_adapter(store_id, platform, store)
        if not adapter:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not create {platform} adapter for store {store_id}",
            )

        # Get request body and headers
        body = await request.body()
        headers = dict(request.headers)

        # Validate webhook signature
        is_valid = await adapter.validate_webhook(headers, body)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )

        # Parse webhook data
        webhook_data = await request.json()
        print(f"======= Webhook data for {store_id}: =======")
        pprint.pprint(webhook_data, indent=2, width=80)

        # Parse incoming message
        incoming_message = await adapter.parse_incoming(webhook_data)
        print(f"======= Incoming message for {store_id}: =======")
        pprint.pprint(incoming_message)

        if not incoming_message:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"message": "No message to process"},
            )

        # Extract platform user ID
        platform_user_id = None
        if platform == "line":
            events = webhook_data.get("events", [])
            if events and events[0].get("source"):
                platform_user_id = events[0]["source"].get("userId")

        if not platform_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No user ID found in webhook",
            )

        # Get or create customer
        customer = customer_service.get_or_create_customer(
            store_id=store_id,
            platform=PlatformType(platform),
            platform_user_id=platform_user_id,
        )
        print(f"======= Customer for {store_id} =======")
        pprint.pprint(customer)

        # Create User object with store context
        user = await adapter.get_user_profile(
            platform_user_id, store_id=store_id, customer_id=customer.customer_id
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not get user profile",
            )
        print(f"======= User for {store_id} =======")
        pprint.pprint(user)

        # Add reply token for LINE
        if platform == "line":
            events = webhook_data.get("events", [])
            if events and events[0].get("replyToken"):
                user.platform_data["reply_token"] = events[0]["replyToken"]

        # Update customer message count
        customer_service.increment_message_count(customer)

        # Process message through gateway with store context
        response_message = await gateway.handle_message(incoming_message, user, store)
        print(f"Response message for {store_id}: {response_message}")

        # Format response for platform
        formatted_response = await adapter.format_outgoing(response_message, user)
        print(f"Formatted response for {store_id}: {formatted_response}")

        # Send response back to platform
        success = await adapter.send_message(formatted_response, user)

        if success:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": "Message processed successfully",
                    "store_id": store_id,
                    "platform": platform,
                    "customer_id": customer.customer_id,
                },
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"message": "Failed to send response"},
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing {platform} webhook for store {store_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


def main():
    """Main function for running the multi-store bot."""
    import uvicorn

    print("🤖 Starting Multi-Store Chat Bot...")
    print("📡 Dynamic webhook endpoints: /webhooks/{platform}/{store_id}")
    print("🔧 Health check: /")
    print("📊 Status endpoint: /status")

    # Show available stores and platforms
    stores = store_service.get_all_stores()
    for store_id, store in stores.items():
        print(f"🏪 Store: {store.name} (ID: {store_id})")
        for platform_name, platform_config in store.platforms.items():
            if platform_config.enabled:
                print(f"   📱 {platform_name}: /webhooks/{platform_name}/{store_id}")

    # Run the FastAPI app
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")


if __name__ == "__main__":
    main()
