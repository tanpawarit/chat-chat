"""
FastAPI application with LINE webhook integration.
"""

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from adapters.platforms.line_adapter import LineAdapter
from bot_gateway.gateway import BotGateway
from config.settings import load_config
from models.platform import LineConfig

# Initialize FastAPI app
app = FastAPI(
    title="Chat Chat Bot",
    description="Multi-platform chatbot with adapter architecture",
    version="1.0.0",
)

# Initialize components
gateway = BotGateway()

# Load configuration from config.yaml
config = load_config()

# LINE configuration
line_config = LineConfig(
    channel_access_token=config["platforms"]["line"]["channel_access_token"],
    channel_secret=config["platforms"]["line"]["channel_secret"],
)

line_adapter = LineAdapter(line_config)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Chat Chat Bot is running!", "status": "healthy"}


@app.get("/status")
async def get_status():
    """Get bot status."""
    gateway_status = gateway.get_status()
    return {
        "bot": gateway_status,
        "adapters": {"line": {"enabled": True, "webhook_path": "/webhooks/line"}},
    }


@app.post("/webhooks/line")
async def line_webhook(request: Request):
    """
    LINE webhook endpoint.

    Handles incoming messages from LINE platform.
    """
    try:
        # Get request body and headers
        body = await request.body()
        headers = dict(request.headers)

        # Validate webhook signature
        is_valid = await line_adapter.validate_webhook(headers, body)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )

        # Parse webhook data
        webhook_data = await request.json()
        print("==========")
        print(f"Webhook data: {webhook_data}")
        print("==========")
        # Parse incoming message
        incoming_message = await line_adapter.parse_incoming(webhook_data)
        print("==========")
        print(f"Incoming message: {incoming_message}")
        print("==========")
        if not incoming_message:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"message": "No message to process"},
            )

        # Get user profile
        platform_user_id = None
        events = webhook_data.get("events", [])
        if events and events[0].get("source"):
            platform_user_id = events[0]["source"].get("userId")

        if not platform_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No user ID found in webhook",
            )

        user = await line_adapter.get_user_profile(platform_user_id)
        print("==========")
        print(f"User: {user}")
        print("==========")
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not get user profile",
            )

        # Add reply token to user data for sending response
        if events and events[0].get("replyToken"):
            user.platform_data["reply_token"] = events[0]["replyToken"]

        # Process message through gateway
        response_message = await gateway.handle_message(incoming_message, user)
        print("==========")
        print(f"Response message: {response_message}")
        print("==========")
        # Format response for LINE
        formatted_response = await line_adapter.format_outgoing(response_message, user)
        print("==========")
        print(f"Formatted response: {formatted_response}")
        print("==========")
        # Send response back to LINE
        success = await line_adapter.send_message(formatted_response, user)

        if success:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"message": "Message processed successfully"},
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"message": "Failed to send response"},
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing LINE webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


def main():
    """Main function for running the bot."""
    import uvicorn

    print("🤖 Starting Chat Chat Bot...")
    print("📡 LINE webhook endpoint: /webhooks/line")
    print("🔧 Health check: /")
    print("📊 Status endpoint: /status")

    # Run the FastAPI app
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")


if __name__ == "__main__":
    main()
