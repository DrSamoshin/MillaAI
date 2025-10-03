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
                request_id = str(uuid.uuid4())
                message_data = {
                    "content": message,
                    "client_msg_id": request_id
                }
                await websocket.send(json.dumps(message_data))

                # Receive all messages for this request_id
                assistant_message_received = False
                while not assistant_message_received:
                    try:
                        response = await websocket.recv()
                    except ConnectionClosed as exc:
                        print(f"Connection closed (code={exc.code}, reason={exc.reason}).")
                        break

                    payload = json.loads(response)

                    # Check if this message belongs to our request
                    message_request_id = payload.get("request_id")
                    if message_request_id != request_id:
                        # This message is from a different request, skip it or handle separately
                        print(f"[DEBUG] Received message with different request_id: {message_request_id} vs {request_id}")
                        continue

                    # Handle each message separately (WebSocket format)
                    if "role" in payload and "content" in payload:
                        role = payload["role"]
                        content = payload["content"]
                        seq = payload.get("seq", "?")
                        msg_id = payload.get("id", "unknown")
                        created_at = payload.get("created_at", "")

                        # Parse timestamp for display
                        timestamp = ""
                        if created_at:
                            try:
                                from datetime import datetime
                                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                                timestamp = dt.strftime("%H:%M:%S")
                            except:
                                timestamp = created_at[:19] if len(created_at) >= 19 else created_at

                        if role == "user":
                            print(f"\033[33m[{timestamp}] You (#{seq}): {content}\033[0m")  # Yellow
                        elif role == "system":
                            # Parse system message content for tool info
                            try:
                                system_data = json.loads(content)
                                tool_calls = system_data.get("tool_calls", [])
                                tool_results = system_data.get("tool_results", [])

                                if tool_calls or tool_results:
                                    print(f"\033[31m[{timestamp}] System (#{seq}): Tool execution\033[0m")  # Red

                                    if tool_calls:
                                        print(f"\033[31m  Tool calls: {len(tool_calls)} functions\033[0m")
                                        for call in tool_calls:
                                            args = call.get('arguments', {})
                                            # Format args more compactly for CLI
                                            if isinstance(args, dict) and len(args) == 1:
                                                # Single argument - show inline
                                                key, value = next(iter(args.items()))
                                                args_str = f"{key}={json.dumps(value)}"
                                            else:
                                                args_str = json.dumps(args)
                                            print(f"\033[31m    {call.get('name', 'unknown')}({args_str})\033[0m")

                                    if tool_results:
                                        print(f"\033[31m  Tool results: {len(tool_results)} responses\033[0m")
                                        for i, result in enumerate(tool_results):
                                            result_data = result.get('result', {})
                                            if isinstance(result_data, dict):
                                                if result_data.get('error'):
                                                    print(f"\033[31m    Result {i+1}: Error - {result_data['error']}\033[0m")
                                                elif result_data.get('success_message'):
                                                    print(f"\033[31m    Result {i+1}: {result_data['success_message']}\033[0m")
                                                else:
                                                    # Show full result data formatted nicely
                                                    formatted_result = json.dumps(result_data, indent=2, ensure_ascii=False)
                                                    print(f"\033[31m    Result {i+1}:\033[0m")
                                                    # Indent each line of the JSON
                                                    for line in formatted_result.split('\n'):
                                                        print(f"\033[31m      {line}\033[0m")
                                            else:
                                                print(f"\033[31m    Result {i+1}: {str(result_data)}\033[0m")
                                else:
                                    # System message without tools
                                    print(f"\033[31m[{timestamp}] System (#{seq}): {content}\033[0m")
                            except json.JSONDecodeError:
                                # Non-JSON system message
                                print(f"\033[31m[{timestamp}] System (#{seq}): {content}\033[0m")

                        elif role == "assistant" and '"tool_calls"' in content:
                            print(f"\033[35m[{timestamp}] Tool (#{seq}): {content}\033[0m")  # Magenta
                            # Don't exit - wait for final assistant message

                        elif role == "assistant":
                            print(f"\033[34m[{timestamp}] Aimi (#{seq}): {content}\033[0m")  # Blue
                            assistant_message_received = True  # Exit loop after assistant message

                        else:
                            print(f"\033[90m[{timestamp}] [{role.upper()}] (#{seq}): {content}\033[0m")

                    # Handle old error format for backward compatibility
                    elif "error" in payload:
                        error_detail = payload.get("error", {})
                        if isinstance(error_detail, dict):
                            print(f"[error] {error_detail.get('message', 'Unknown error')}")
                        else:
                            print(f"[error] {error_detail}")
                        assistant_message_received = True  # Exit on error

                    else:
                        print(f"[unknown] {payload}")
                        assistant_message_received = True  # Exit on unknown format

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
