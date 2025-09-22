"""Interactive chat client for Aimi - New chat system."""

from __future__ import annotations

import asyncio
import json
import sys
import uuid

import websockets
from websockets.exceptions import ConnectionClosed


async def chat_loop(token: str, chat_id: str) -> None:
    """Main chat loop with WebSocket connection."""
    headers = {"Authorization": f"Bearer {token}"}
    url = f"ws://127.0.0.1:8000/v1/ws/chat/{chat_id}"

    print(f"Connecting to chat {chat_id}...")

    async for websocket in websockets.connect(url, additional_headers=headers):
        print(f"Connected! Chat ID: {chat_id}")
        print("Type messages, 'exit' to quit.")

        try:
            while True:
                try:
                    message = await asyncio.get_event_loop().run_in_executor(
                        None, sys.stdin.readline
                    )
                except KeyboardInterrupt:
                    message = "exit\n"

                if not message:
                    message = "exit\n"

                message = message.strip()
                if message.lower() in {"exit", "quit"}:
                    await websocket.close()
                    print("Disconnected.")
                    return

                if not message:
                    continue

                # Send message in new JSON format
                message_data = {
                    "content": message,
                    "client_msg_id": str(uuid.uuid4())
                }
                await websocket.send(json.dumps(message_data))

                try:
                    response = await websocket.recv()
                except ConnectionClosed as exc:
                    print(f"Connection closed (code={exc.code}, reason={exc.reason}).")
                    break

                payload = json.loads(response)

                # Handle thinking message
                if payload.get("status") == "thinking":
                    print(f"[thinking] {payload.get('message', 'Processing...')}")
                    # Wait for actual response
                    response = await websocket.recv()
                    payload = json.loads(response)

                # Debug: show what we received
                print(f"[DEBUG] Received: {payload}")

                # Handle response
                if "error" in payload:
                    error_detail = payload.get("error", {})
                    if isinstance(error_detail, dict):
                        print(f"[error] {error_detail.get('message', 'Unknown error')}")
                    else:
                        print(f"[error] {error_detail}")
                elif payload.get("status") == "success" and "data" in payload:
                    data = payload["data"]
                    print(f"Aimi: {data['assistant_message']['content']}")
                else:
                    print(f"[unknown] {payload}")

        finally:
            await asyncio.sleep(1)


def get_user_input(prompt: str, default: str = None) -> str:
    """Get user input with optional default value."""
    if default:
        response = input(f"{prompt} [{default}]: ").strip()
        return response if response else default
    else:
        while True:
            response = input(f"{prompt}: ").strip()
            if response:
                return response
            print("This field is required.")


def main() -> None:
    """Main entry point for chat CLI."""
    print("=== Aimi Chat Client ===")

    # Get token from user
    token = get_user_input("Enter access token")

    # Get or generate chat ID
    print("\nChat ID options:")
    print("1. Enter existing chat ID")
    print("2. Generate new chat ID")

    choice = get_user_input("Choose option (1/2)", "2")

    if choice == "1":
        chat_id = get_user_input("Enter chat ID")
    else:
        chat_id = str(uuid.uuid4())
        print(f"Generated new chat ID: {chat_id}")

    print(f"\nStarting chat session...")

    try:
        asyncio.run(chat_loop(token, chat_id))
    except KeyboardInterrupt:
        print("\nInterrupted.")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
