import os
import sys
import json
import asyncio
import logging
import httpx
from nats.aio.client import Client as NATS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Configuration
NATS_URL = os.getenv("NATS_URL", "nats://my-nats:4222")
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID", "")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
DISCORD_ENABLED = os.getenv("DISCORD_ENABLED", "true").lower() == "true"
NATS_SUBJECT = "todos"
QUEUE_GROUP = "broadcasters"  # Queue group ensures only one subscriber processes each message


async def send_discord_message(message: str):
    """Send a message to Discord channel using bot"""
    if not DISCORD_CHANNEL_ID or not DISCORD_BOT_TOKEN:
        logger.warning("Discord credentials not configured, skipping message")
        return False
    
    url = f"https://discord.com/api/channels/{DISCORD_CHANNEL_ID}/messages"
    headers = {
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {"content": message}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                logger.info(f"Successfully sent message to Discord: {message[:50]}...")
                return True
            else:
                logger.error(f"Failed to send Discord message: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        logger.error(f"Error sending Discord message: {e}")
        return False


async def message_handler(msg):
    """Handle incoming NATS messages"""
    try:
        data = json.loads(msg.data.decode())
        action = data.get("action", "unknown")
        todo = data.get("todo", {})
        timestamp = data.get("timestamp", "N/A")
        
        todo_id = todo.get("id", "?")
        todo_text = todo.get("todo", "")
        done_status = todo.get("done", False)
        
        # Build verbose message with full details
        if action == "created":
            emoji = "📝"
            action_text = "NEW TODO CREATED"
        elif action == "updated":
            emoji = "✅" if done_status else "🔄"
            action_text = "TODO MARKED COMPLETE" if done_status else "TODO REOPENED"
        else:
            emoji = "ℹ️"
            action_text = f"TODO ACTION: {action.upper()}"
        
        message = f"""
{emoji} **{action_text}** {emoji}
━━━━━━━━━━━━━━━━━━━━━
**ID:** {todo_id}
**Task:** {todo_text}
**Status:** {"✅ Done" if done_status else "⏳ Pending"}
**Timestamp:** {timestamp}
━━━━━━━━━━━━━━━━━━━━━
```json
{json.dumps(data, indent=2)}
```
""".strip()
        
        logger.info(f"Received {action} event for todo {todo_id}")
        
        if DISCORD_ENABLED:
            await send_discord_message(message)
        else:
            logger.info(f"[LOG ONLY MODE] Would send to Discord:\n{message}")
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode message: {e}")
    except Exception as e:
        logger.error(f"Error processing message: {e}")


async def main():
    """Main function to connect to NATS and subscribe to messages"""
    nc = NATS()
    
    # Retry connection with backoff
    max_retries = 10
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Connecting to NATS at {NATS_URL} (attempt {attempt + 1}/{max_retries})")
            await nc.connect(servers=[NATS_URL])
            logger.info("Successfully connected to NATS")
            break
        except Exception as e:
            logger.warning(f"Failed to connect to NATS: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error("Max retries reached, exiting")
                return
    
    # Subscribe to the todos subject with a queue group
    # Queue group ensures that only ONE subscriber in the group receives each message
    # This prevents duplicate messages when scaling to multiple replicas
    await nc.subscribe(NATS_SUBJECT, queue=QUEUE_GROUP, cb=message_handler)
    logger.info(f"Subscribed to '{NATS_SUBJECT}' with queue group '{QUEUE_GROUP}'")
    logger.info("Broadcaster is ready and waiting for messages...")
    
    # Keep the connection alive
    try:
        while True:
            await asyncio.sleep(1)
            if not nc.is_connected:
                logger.warning("Lost connection to NATS, attempting to reconnect...")
                await nc.connect(servers=[NATS_URL])
    except KeyboardInterrupt:
        logger.info("Shutting down broadcaster...")
    finally:
        await nc.drain()
        await nc.close()


if __name__ == "__main__":
    logger.info("Starting Broadcaster service...")
    if DISCORD_ENABLED:
        logger.info("Discord notifications: ENABLED")
    else:
        logger.info("Discord notifications: DISABLED (log only mode)")
    asyncio.run(main())

