"""Telegram channel implementation using python-telegram-bot v21+.

Long-polling mode, handles text/photos/documents/voice, splits long
responses, sends typing indicators, and only responds in private DMs
by default.
"""

from __future__ import annotations

import logging
import os
import tempfile
import time

from telegram import Update
from telegram.constants import ChatAction, ChatType, ParseMode
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
)

from antidote.channels.base import BaseChannel, IncomingMessage, OutgoingMessage
from antidote.config import Config

logger = logging.getLogger(__name__)

# Telegram maximum message length
MAX_MESSAGE_LENGTH = 4096


def _split_message(text: str) -> list[str]:
    """Split text into chunks of at most MAX_MESSAGE_LENGTH characters.

    Tries to split at paragraph boundaries (double newline), falling
    back to single newlines, then hard-split at the limit.
    """
    if len(text) <= MAX_MESSAGE_LENGTH:
        return [text]

    chunks: list[str] = []
    remaining = text

    while remaining:
        if len(remaining) <= MAX_MESSAGE_LENGTH:
            chunks.append(remaining)
            break

        # Try to split at paragraph boundary
        split_pos = remaining.rfind("\n\n", 0, MAX_MESSAGE_LENGTH)
        if split_pos == -1:
            # Try single newline
            split_pos = remaining.rfind("\n", 0, MAX_MESSAGE_LENGTH)
        if split_pos == -1:
            # Try space
            split_pos = remaining.rfind(" ", 0, MAX_MESSAGE_LENGTH)
        if split_pos == -1:
            # Hard split
            split_pos = MAX_MESSAGE_LENGTH

        chunks.append(remaining[:split_pos])
        remaining = remaining[split_pos:].lstrip()

    return chunks


class TelegramChannel(BaseChannel):
    """Telegram bot channel using long-polling."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._app: Application | None = None
        self._on_message: callable | None = None

    def _get_bot_token(self) -> str:
        """Get bot token from secrets store, falling back to env var."""
        token = self._config.get_secret("TELEGRAM_BOT_TOKEN")
        if not token:
            token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not token:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN not found. Run the setup wizard or set "
                "the TELEGRAM_BOT_TOKEN environment variable."
            )
        return token

    async def start(self, on_message: callable) -> None:
        """Start the Telegram bot with long-polling."""
        self._on_message = on_message
        token = self._get_bot_token()

        self._app = Application.builder().token(token).build()

        # Register handler for all message types we support
        self._app.add_handler(
            MessageHandler(
                filters.TEXT | filters.PHOTO | filters.Document.ALL | filters.VOICE,
                self._handle_update,
            )
        )

        # Initialize and start polling
        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling(drop_pending_updates=True)

        logger.info("Telegram bot started (long-polling mode)")

        # Keep running until stopped
        # The caller (main.py) handles signals and calls stop()

    async def send(self, message: OutgoingMessage) -> None:
        """Send a message (or multiple if text is long)."""
        if self._app is None:
            raise RuntimeError("Bot not started")

        chunks = _split_message(message.text)
        for chunk in chunks:
            await self._send_chunk(message.chat_id, chunk, message.reply_to)

    async def _send_chunk(
        self, chat_id: str, text: str, reply_to: str | None = None
    ) -> None:
        """Send a single text chunk, trying Markdown first then plain text."""
        kwargs: dict = {
            "chat_id": int(chat_id),
            "text": text,
        }
        if reply_to:
            kwargs["reply_to_message_id"] = int(reply_to)

        try:
            kwargs["parse_mode"] = ParseMode.MARKDOWN
            await self._app.bot.send_message(**kwargs)
        except Exception:
            # Markdown failed -- fall back to plain text
            kwargs.pop("parse_mode", None)
            try:
                await self._app.bot.send_message(**kwargs)
            except Exception as e:
                logger.error("Failed to send message to %s: %s", chat_id, e)

    async def stop(self) -> None:
        """Gracefully stop the bot."""
        if self._app is not None:
            if self._app.updater and self._app.updater.running:
                await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()
            self._app = None
            logger.info("Telegram bot stopped")

    async def _handle_update(self, update: Update, context) -> None:
        """Handle an incoming Telegram update."""
        message = update.effective_message
        if message is None:
            return

        chat = update.effective_chat
        if chat is None:
            return

        # Only respond in private DMs by default
        if chat.type != ChatType.PRIVATE:
            return

        sender = update.effective_user
        sender_id = str(sender.id) if sender else "unknown"
        sender_name = sender.full_name if sender else "Unknown"
        chat_id = str(chat.id)

        # Build the IncomingMessage
        text = message.text or message.caption or ""
        media: list[dict] | None = None

        # Handle photos
        if message.photo:
            # Get the largest photo size
            photo = message.photo[-1]
            file = await photo.get_file()
            temp_path = os.path.join(tempfile.gettempdir(), f"antidote_photo_{photo.file_id}.jpg")
            await file.download_to_drive(temp_path)
            media = [{"type": "photo", "url": temp_path, "caption": message.caption or ""}]
            if not text:
                text = "[Photo received]"

        # Handle documents
        if message.document:
            doc = message.document
            file = await doc.get_file()
            temp_path = os.path.join(tempfile.gettempdir(), f"antidote_doc_{doc.file_name or doc.file_id}")
            await file.download_to_drive(temp_path)
            media = media or []
            media.append({"type": "document", "url": temp_path, "caption": doc.file_name or ""})
            if not text:
                text = f"[Document received: {doc.file_name or 'unnamed'}]"

        # Handle voice messages
        if message.voice:
            voice = message.voice
            file = await voice.get_file()
            temp_path = os.path.join(tempfile.gettempdir(), f"antidote_voice_{voice.file_id}.ogg")
            await file.download_to_drive(temp_path)
            media = media or []
            media.append({"type": "voice", "url": temp_path, "caption": ""})
            if not text:
                text = "[Voice message received. Transcription is not yet available.]"

        if not text:
            return

        incoming = IncomingMessage(
            text=text,
            sender_id=sender_id,
            sender_name=sender_name,
            chat_id=chat_id,
            timestamp=message.date.timestamp() if message.date else time.time(),
            media=media,
        )

        # Send typing indicator
        try:
            await self._app.bot.send_chat_action(
                chat_id=int(chat_id), action=ChatAction.TYPING
            )
        except Exception:
            pass  # Non-critical

        # Process the message
        try:
            response = await self._on_message(incoming)
            if response:
                await self.send(OutgoingMessage(text=response, chat_id=chat_id))
        except Exception as e:
            logger.exception("Error processing message from %s", sender_name)
            error_text = (
                "Sorry, something went wrong while processing your message. "
                "Please try again."
            )
            try:
                await self.send(OutgoingMessage(text=error_text, chat_id=chat_id))
            except Exception:
                logger.error("Failed to send error message to %s", chat_id)
