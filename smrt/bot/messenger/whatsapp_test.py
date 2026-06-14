#!/usr/bin/env python3
"""
Evolution API WebSocket event listener.
Connects to a single instance and prints all incoming events.
"""

import json
import signal
import sys
import socketio

EVOLUTION_SERVER = "http://192.168.2.50:6080"
INSTANCE = "smrt-me"
API_KEY = "76C93EC1332F-4466-9FDB-8E9CA382660E"

ALL_EVENTS = [
    "APPLICATION_STARTUP",
    "QRCODE_UPDATED",
    "MESSAGES_SET",
    "MESSAGES_UPSERT",
    "MESSAGES_UPDATE",
    "MESSAGES_DELETE",
    "SEND_MESSAGE",
    "CONTACTS_SET",
    "CONTACTS_UPSERT",
    "CONTACTS_UPDATE",
    "PRESENCE_UPDATE",
    "CHATS_SET",
    "CHATS_UPSERT",
    "CHATS_UPDATE",
    "CHATS_DELETE",
    "GROUPS_UPSERT",
    "GROUP_UPDATE",
    "GROUP_PARTICIPANTS_UPDATE",
    "CONNECTION_UPDATE",
    "LABELS_EDIT",
    "LABELS_ASSOCIATION",
    "CALL",
    "TYPEBOT_START",
    "TYPEBOT_CHANGE_STATUS",
]

sio = socketio.Client(logger=False, engineio_logger=False)


def print_event(event_name: str, data):
    print(f"\n=== {event_name} ===")
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


@sio.on("connect")
def on_connect():
    print(f"[+] Connected to {EVOLUTION_SERVER}/{INSTANCE}")


@sio.on("disconnect")
def on_disconnect():
    print("[-] Disconnected")


@sio.on("connect_error")
def on_connect_error(err):
    print(f"[!] Connection error: {err}")


# Register a handler for every known event
for _event in ALL_EVENTS:
    # Use a default-argument closure to capture the event name
    def _make_handler(name):
        @sio.on(name.lower().replace("_", "."))
        def handler(data):
            print_event(name, data)
        # Some servers emit with the original casing too
        @sio.on(name)
        def handler_upper(data):
            print_event(name, data)
    _make_handler(_event)


def main():
    url = f"{EVOLUTION_SERVER.rstrip('/')}/{INSTANCE}"
    print(f"Connecting to {url} ...")

    try:
        sio.connect(
            url,
            transports=["websocket"],
            headers={"apikey": API_KEY},
        )
    except Exception as e:
        print(f"[!] Failed to connect: {e}")
        sys.exit(1)

    def _shutdown(sig, frame):
        print("\nShutting down...")
        sio.disconnect()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    print("Listening for events. Press Ctrl+C to stop.\n")
    sio.wait()


if __name__ == "__main__":
    main()