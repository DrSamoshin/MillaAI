"""Simple interactive chat client for Aimi."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Optional
from uuid import UUID, uuid4

import websockets
from websockets.exceptions import ConnectionClosed

DEFAULT_WS_URL = "ws://127.0.0.1:8000/ws/chat"


async def chat_loop(url: str, user_id: UUID) -> None:
    async for websocket in websockets.connect(f"{url}?user_id={user_id}"):
        print(f"Connected to {url} as {user_id}. Type messages, 'exit' to quit.")
        try:
            while True:
                try:
                    message = await asyncio.get_event_loop().run_in_executor(
                        None, sys.stdin.readline
                    )
                except KeyboardInterrupt:  # pragma: no cover
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
                await websocket.send(message)
                try:
                    response = await websocket.recv()
                except ConnectionClosed as exc:
                    print(f"Connection closed (code={exc.code}, reason={exc.reason}).")
                    break
                payload = json.loads(response)
                if "error" in payload:
                    detail = payload.get("detail") or payload.get("error")
                    print(f"[error] {detail}")
                else:
                    print(f"Aimi: {payload.get('reply')}")
        finally:
            await asyncio.sleep(1)


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aimi chat CLI")
    parser.add_argument(
        "--url", default=DEFAULT_WS_URL, help="WebSocket endpoint, default %(default)s"
    )
    parser.add_argument(
        "--user-id",
        type=UUID,
        default=None,
        help="Existing user UUID. If omitted, random UUID",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> None:
    args = parse_args(argv)
    user_id = args.user_id or uuid4()
    try:
        asyncio.run(chat_loop(args.url, user_id))
    except KeyboardInterrupt:  # pragma: no cover
        print("\nInterrupted.")


if __name__ == "__main__":
    main()
