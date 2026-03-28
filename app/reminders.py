"""
Reminders module.
- Creates Google Calendar events (optional)
- Schedules repeated Telegram reminder messages:
    1 day before, 1 hour before, and at the exact time
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")
CREDS_FILE  = Path(os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json"))
REMINDERS_FILE = Path(os.getenv("REMINDERS_FILE", "app/storage/reminders.json"))

# Will be set by main.py after bot starts
telegram_app = None
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def set_telegram_app(app):
    global telegram_app
    telegram_app = app


def create_reminder(title: str, date: str, time: str = "09:00", sender_name: str = ""):
    """Save reminder and schedule Telegram notifications."""
    _save_reminder(title, date, time, sender_name)
    _create_google_event(title, date, time, sender_name)


def _save_reminder(title: str, date: str, time: str, sender_name: str):
    """Persist reminder to JSON so it survives restarts."""
    REMINDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    reminders = _load_reminders()

    reminder_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    reminders.append({
        "title": title,
        "datetime": reminder_dt.isoformat(),
        "sender": sender_name,
        "notified_day":  False,
        "notified_hour": False,
        "notified_exact": False,
    })
    REMINDERS_FILE.write_text(json.dumps(reminders, indent=2))


def _load_reminders() -> list:
    if REMINDERS_FILE.exists():
        try:
            return json.loads(REMINDERS_FILE.read_text())
        except Exception:
            return []
    return []


async def reminder_scheduler():
    """
    Runs forever in the background.
    Checks every minute if any reminder needs to be sent.
    Sends notifications at:
      - 1 day before
      - 1 hour before
      - Exact time
    """
    while True:
        await asyncio.sleep(60)   # check every minute
        now = datetime.now()
        reminders = _load_reminders()
        changed = False

        for r in reminders:
            reminder_dt = datetime.fromisoformat(r["datetime"])

            # Skip past reminders that are fully done
            if reminder_dt < now - timedelta(minutes=1):
                continue

            diff = reminder_dt - now  # time remaining

            # 1 day before (within a 1-minute window)
            if not r["notified_day"] and timedelta(hours=23, minutes=59) >= diff >= timedelta(hours=23, minutes=58):
                await _send_reminder(r["title"], "Tomorrow", r["sender"])
                r["notified_day"] = True
                changed = True

            # 1 hour before (within a 1-minute window)
            elif not r["notified_hour"] and timedelta(minutes=60) >= diff >= timedelta(minutes=59):
                await _send_reminder(r["title"], "In 1 hour", r["sender"])
                r["notified_hour"] = True
                changed = True

            # Exact time (within a 1-minute window)
            elif not r["notified_exact"] and timedelta(minutes=1) >= diff >= timedelta(seconds=0):
                await _send_reminder(r["title"], "Right now", r["sender"])
                r["notified_exact"] = True
                changed = True

        if changed:
            REMINDERS_FILE.write_text(json.dumps(reminders, indent=2))


async def _send_reminder(title: str, when: str, sender: str):
    """Send a reminder message to the Telegram group."""
    if not telegram_app or not CHAT_ID:
        print(f"[reminder] Would send: {when} — {title}")
        return

    emoji = "⏰" if when == "Right now" else "🔔"
    message = (
        f"{emoji} *Reminder — {when}!*\n"
        f"{title}\n"
        f"_(set by {sender})_"
    )
    try:
        await telegram_app.bot.send_message(
            chat_id=CHAT_ID,
            text=message,
            parse_mode="Markdown",
        )
        print(f"[reminder] Sent: {when} — {title}")
    except Exception as e:
        print(f"[reminder] Failed to send: {e}")


def _create_google_event(title: str, date: str, time: str, sender_name: str):
    """Optional — create a Google Calendar event."""
    if not CREDS_FILE.exists():
        print(f"[calendar] No credentials.json — skipping: {title}")
        return

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds = service_account.Credentials.from_service_account_file(
            str(CREDS_FILE),
            scopes=["https://www.googleapis.com/auth/calendar"],
        )
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)

        start_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        end_dt   = start_dt + timedelta(hours=1)
        tz       = os.getenv("TIMEZONE", "America/Los_Angeles")

        event = {
            "summary": title,
            "description": f"Set by {sender_name} via the family bot.",
            "start": {"dateTime": start_dt.isoformat(), "timeZone": tz},
            "end":   {"dateTime": end_dt.isoformat(),   "timeZone": tz},
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": 60},
                    {"method": "email", "minutes": 60},
                ],
            },
        }
        service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        print(f"[calendar] Created: {title} on {date} at {time}")

    except Exception as e:
        print(f"[calendar] Error: {e}")
