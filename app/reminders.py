"""
Google Calendar integration — creates events when the bot detects a reminder.
Optional: the bot works fine without this, it just won't create calendar events.
"""

import os
from datetime import datetime, timedelta
from pathlib import Path

CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")
CREDS_FILE  = Path(os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json"))


def create_reminder(title: str, date: str, time: str = "09:00", sender_name: str = ""):
    if not CREDS_FILE.exists():
        print(f"[calendar] No credentials.json — skipping reminder: {title}")
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
