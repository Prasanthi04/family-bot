"""
Core bot logic — Claude AI integration.
Maintains per-user conversation history and detects reminder intents.
"""

import os
import json
import re
from datetime import datetime, timezone
from anthropic import AsyncAnthropic

from .memory import get_history, save_turn
from .reminders import create_reminder

anthropic = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
model="claude-sonnet-4-20250514"
FAMILY_NAME = os.getenv("FAMILY_NAME", "Our Family")

SYSTEM_PROMPT = """You are the family assistant bot for the {family_name} family on Telegram.
Your job is to help with:
  - Vacation and trip planning (itineraries, packing lists, budgets, local tips)
  - Reminders (e.g. "remind us to renew passports next Monday")
  - General questions the family asks

Rules:
  - Keep replies concise — this is a chat app, not an essay.
  - Use plain text with dashes (-) for lists. Avoid heavy markdown.
  - Be warm, friendly and helpful. You know this family well.
  - Today's date is {today}.
  - When someone asks for a reminder, confirm it in your reply AND include
    a hidden JSON block at the very end (the user won't see it) in this exact format:
    [REMINDER]{{"title": "...", "date": "YYYY-MM-DD", "time": "HH:MM"}}[/REMINDER]
  - If you're unsure of a date, make a reasonable assumption and mention it.
"""


async def handle_message(sender_id: str, sender_name: str, query: str) -> str:
    today = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")

    history = get_history(sender_id)
    history.append({"role": "user", "content": f"{sender_name} asks: {query}"})

    response = await anthropic.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=SYSTEM_PROMPT.format(family_name=FAMILY_NAME, today=today),
        messages=history[-20:],
    )

    reply_text = response.content[0].text
    save_turn(sender_id, query, reply_text, sender_name)

    # Parse and handle reminder if Claude included one
    reminder_match = re.search(
        r"\[REMINDER\](.*?)\[/REMINDER\]", reply_text, re.DOTALL
    )
    if reminder_match:
        try:
            data = json.loads(reminder_match.group(1).strip())
            create_reminder(
                title=data["title"],
                date=data["date"],
                time=data.get("time", "09:00"),
                sender_name=sender_name,
            )
        except Exception as e:
            print(f"[bot] Reminder parse error: {e}")

        # Strip the hidden block before sending to user
        reply_text = re.sub(
            r"\[REMINDER\].*?\[/REMINDER\]", "", reply_text, flags=re.DOTALL
        ).strip()

    return reply_text
