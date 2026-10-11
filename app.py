import hmac
import os

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

if not BOT_TOKEN:
    raise RuntimeError("Missing BOT_TOKEN environment variable. Add it in Render Environment settings.")
if not WEBHOOK_SECRET:
    raise RuntimeError("Missing WEBHOOK_SECRET environment variable. Add it in Render Environment settings.")


def telegram_api(method: str, payload: dict) -> dict:
    response = requests.post(f"{TELEGRAM_API}/{method}", json=payload, timeout=15)
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API error: {data}")
    return data


def setup_webhook() -> None:
    base_url = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
    if not base_url:
        print("RENDER_EXTERNAL_URL not available; webhook was not configured automatically.")
        return
    try:
        result = telegram_api(
            "setWebhook",
            {
                "url": f"{base_url}/webhook",
                "secret_token": WEBHOOK_SECRET,
                "drop_pending_updates": True,
            },
        )
        print("Telegram webhook setup result:", result)
    except Exception as exc:
        print("WARNING: Could not configure Telegram webhook:", repr(exc))


setup_webhook()


@app.get("/")
def home():
    return "Hello! Telegram bot server is running successfully.", 200


@app.post("/webhook")
def webhook():
    incoming_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not hmac.compare_digest(incoming_secret, WEBHOOK_SECRET):
        return "Unauthorized", 403

    update = request.get_json(silent=True) or {}
    message = update.get("message") or update.get("edited_message")

    if message and message.get("text"):
        chat_id = message["chat"]["id"]
        incoming_text = message["text"].strip()
        command = incoming_text.split(maxsplit=1)[0].split("@")[0] if incoming_text else ""

        if command == "/start":
            reply = "Hello! Your bot is running successfully. ✅"
        elif command == "/help":
            reply = "Test bot is working. Send /start to see the welcome message."
        else:
            reply = f"You sent: {incoming_text}"

        try:
            telegram_api("sendMessage", {"chat_id": chat_id, "text": reply})
        except Exception as exc:
            print("Failed to send Telegram reply:", repr(exc))
            return jsonify(ok=False), 500

    return jsonify(ok=True), 200
