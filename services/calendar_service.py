from typing import List, Optional
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import logging

logger = logging.getLogger(__name__)

class CalendarEvent:
    def __init__(self, event_id: str, title: str, start_time: datetime, end_time: datetime, description: str = "", location: str = ""):
        self.event_id = event_id
        self.title = title
        self.start_time = start_time
        self.end_time = end_time
        self.description = description
        self.location = location

class CalendarService:
    def __init__(self, token_data):
        self.creds = Credentials(**token_data)
        self.service = build('calendar', 'v3', credentials=self.creds)

    def get_freebusy(self, email, start, end):
        """Get free/busy information for a calendar"""
        try:
            body = {
                "timeMin": start.isoformat() + "Z",
                "timeMax": end.isoformat() + "Z",
                "items": [{"id": email}]
            }
            events_result = self.service.freebusy().query(body=body).execute()
            return events_result['calendars'][email]['busy']
        except Exception as e:
            logger.error(f"Error getting freebusy data: {str(e)}")
            return []

    def create_event(self, calendar_id, title, start, end, description="", location=""):
        """Create event in Google Calendar"""
        try:
            event = {
                'summary': title,
                'start': {'dateTime': start.isoformat(), 'timeZone': 'UTC'},
                'end': {'dateTime': end.isoformat(), 'timeZone': 'UTC'},
            }
            if description:
                event['description'] = description
            if location:
                event['location'] = location

            event_result = self.service.events().insert(calendarId=calendar_id, body=event).execute()
            return event_result['id']
        except Exception as e:
            logger.error(f"Error creating event: {str(e)}")
            return None

    def get_free_slots(self, user_email: str, start: datetime, end: datetime) -> List[datetime]:
        """Return list of free datetime slots for user between start and end."""
        try:
            busy_times = self.get_freebusy(user_email, start, end)
            # Implementation would analyze busy times and return free slots
            # For now, return empty list as this is a complex feature
            return []
        except Exception as e:
            logger.error(f"Error getting free slots: {str(e)}")
            return []

    def list_events(self, calendar_id: str = 'primary', time_min: Optional[datetime] = None, time_max: Optional[datetime] = None) -> List[CalendarEvent]:
        """List events in the user's calendar between time_min and time_max."""
        try:
            events_params = {
                'calendarId': calendar_id,
                'singleEvents': True,
                'orderBy': 'startTime'
            }

            if time_min:
                events_params['timeMin'] = time_min.isoformat() + 'Z'
            if time_max:
                events_params['timeMax'] = time_max.isoformat() + 'Z'

            events_result = self.service.events().list(**events_params).execute()
            events = events_result.get('items', [])

            calendar_events = []
            for event in events:
                start_time = event['start'].get('dateTime', event['start'].get('date'))
                end_time = event['end'].get('dateTime', event['end'].get('date'))

                # Parse datetime strings
                if 'T' in start_time:
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                else:
                    # All-day event
                    start_dt = datetime.fromisoformat(start_time + 'T00:00:00')
                    end_dt = datetime.fromisoformat(end_time + 'T23:59:59')

                calendar_events.append(CalendarEvent(
                    event_id=event['id'],
                    title=event.get('summary', 'No Title'),
                    start_time=start_dt,
                    end_time=end_dt,
                    description=event.get('description', ''),
                    location=event.get('location', '')
                ))

            return calendar_events
        except Exception as e:
            logger.error(f"Error listing events: {str(e)}")
            return []

    def add_event(self, event: CalendarEvent, calendar_id: str = 'primary') -> str:
        """Add event, return event_id."""
        try:
            google_event = {
                'summary': event.title,
                'start': {'dateTime': event.start_time.isoformat(), 'timeZone': 'UTC'},
                'end': {'dateTime': event.end_time.isoformat(), 'timeZone': 'UTC'},
            }

            if event.description:
                google_event['description'] = event.description
            if event.location:
                google_event['location'] = event.location

            result = self.service.events().insert(calendarId=calendar_id, body=google_event).execute()
            return result['id']
        except Exception as e:
            logger.error(f"Error adding event: {str(e)}")
            return ""

    def remove_event(self, event_id: str, calendar_id: str = 'primary') -> bool:
        """Remove event by id."""
        try:
            self.service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error removing event: {str(e)}")
            return False

    def update_event(self, event: CalendarEvent, calendar_id: str = 'primary') -> bool:
        """Update event info."""
        try:
            # First get the existing event
            existing_event = self.service.events().get(calendarId=calendar_id, eventId=event.event_id).execute()

            # Update fields
            existing_event['summary'] = event.title
            existing_event['start'] = {'dateTime': event.start_time.isoformat(), 'timeZone': 'UTC'}
            existing_event['end'] = {'dateTime': event.end_time.isoformat(), 'timeZone': 'UTC'}

            if event.description:
                existing_event['description'] = event.description
            if event.location:
                existing_event['location'] = event.location

            # Update the event
            self.service.events().update(
                calendarId=calendar_id,
                eventId=event.event_id,
                body=existing_event
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating event: {str(e)}")
            return False

    def add_event_to_user_calendar(self, user_calendar_id: str, event_title: str, start_time: datetime, end_time: datetime, description: str = "", location: str = "") -> bool:
        """Add event to a user's personal calendar"""
        try:
            return self.create_event(user_calendar_id, event_title, start_time, end_time, description, location) is not None
        except Exception as e:
            logger.error(f"Error adding event to user calendar: {str(e)}")
            return False

