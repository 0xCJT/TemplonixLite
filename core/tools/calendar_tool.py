#########################################################################################
# CalendarTool: Uses Google Calendar API to create events and send invites.
#########################################################################################
import logging
import os
import signal
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class CalendarTool:
    #########################################################################################
    # Initialize the tool with Google Calendar API credentials.
    #########################################################################################
    def __init__(self, config) -> None:
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.tool_name = "CALENDAR_TOOL"
        
        # Google Calendar API scopes
        self.SCOPES = ['https://www.googleapis.com/auth/calendar']
        
        # Initialize the service
        self.service = self._get_calendar_service()

    #########################################################################################
    # Authenticate and get Google Calendar service.
    #########################################################################################
    def _get_calendar_service(self):
        """Get authenticated Google Calendar service."""
        creds = None
        # The file token.json stores the user's access and refresh tokens.
        # Look for credentials.json in the project root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        token_path = os.path.join(project_root, 'token.json')
        credentials_path = os.path.join(project_root, 'credentials.json')
        
        self.logger.info(f"CALENDAR_TOOL :: Looking for credentials at: {credentials_path}")
        self.logger.info(f"CALENDAR_TOOL :: Project root: {project_root}")
        
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, self.SCOPES)
        
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    self.logger.info("CALENDAR_TOOL :: Refreshing expired credentials...")
                    creds.refresh(Request())
                except Exception as e:
                    self.logger.error(f"CALENDAR_TOOL :: Failed to refresh credentials: {e}")
                    creds = None
            
            if not creds:
                if os.path.exists(credentials_path):
                    try:
                        self.logger.info("CALENDAR_TOOL :: Starting OAuth flow...")
                        flow = InstalledAppFlow.from_client_secrets_file(credentials_path, self.SCOPES)
                        # Use console flow instead of local server to avoid browser issues
                        creds = flow.run_console()
                        self.logger.info("CALENDAR_TOOL :: OAuth flow completed successfully")
                    except Exception as e:
                        self.logger.error(f"CALENDAR_TOOL :: OAuth flow failed: {e}")
                        # Fallback to local server if console flow fails
                        try:
                            self.logger.info("CALENDAR_TOOL :: Trying local server flow...")
                            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, self.SCOPES)
                            creds = flow.run_local_server(port=8080, open_browser=True)
                            self.logger.info("CALENDAR_TOOL :: Local server OAuth flow completed successfully")
                        except Exception as e2:
                            self.logger.error(f"CALENDAR_TOOL :: Both OAuth flows failed: {e2}")
                            raise Exception(f"OAuth authentication failed: {e2}")
                else:
                    self.logger.error("credentials.json not found. Please download from Google Cloud Console.")
                    raise FileNotFoundError("Google Calendar credentials not found")
            
            # Save the credentials for the next run
            try:
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
                self.logger.info("CALENDAR_TOOL :: Credentials saved successfully")
            except Exception as e:
                self.logger.error(f"CALENDAR_TOOL :: Failed to save credentials: {e}")

        return build('calendar', 'v3', credentials=creds)

    #########################################################################################
    # Create a calendar event and send invites to attendees.
    #########################################################################################
    def create_event(
        self,
        title: str,
        description: str = "",
        start_datetime: Optional[str] = None,
        end_datetime: Optional[str] = None,
        duration_minutes: int = 60,
        attendees: Optional[List[str]] = None,
        location: str = "",
        send_notifications: bool = True,
        timezone: str = "Europe/London"
    ) -> str:
        """
        Create a Google Calendar event and send invites.
        
        Args:
            title: Event title
            description: Event description
            start_datetime: Start time in ISO format (YYYY-MM-DDTHH:MM:SS) or None for now
            end_datetime: End time in ISO format or None to use duration
            duration_minutes: Duration in minutes if end_datetime not provided
            attendees: List of email addresses to invite
            location: Event location
            send_notifications: Whether to send email notifications to attendees
            timezone: Timezone for the event (defaults to Europe/London)
            
        Returns:
            Event details or error message
        """
        try:
            # Parse start time
            if start_datetime:
                start_time = datetime.fromisoformat(start_datetime.replace('Z', '+00:00'))
            else:
                start_time = datetime.now()
            
            # Parse end time
            if end_datetime:
                end_time = datetime.fromisoformat(end_datetime.replace('Z', '+00:00'))
            else:
                end_time = start_time + timedelta(minutes=duration_minutes)
            
            # Format times for Google Calendar API
            start_time_str = start_time.isoformat()
            end_time_str = end_time.isoformat()
            
            # Build attendees list
            attendees_list = []
            if attendees:
                for email in attendees:
                    attendees_list.append({'email': email})
            
            # Create event body
            event_body = {
                'summary': title,
                'description': description,
                'start': {
                    'dateTime': start_time_str,
                    'timeZone': timezone,
                },
                'end': {
                    'dateTime': end_time_str,
                    'timeZone': timezone,
                },
                'attendees': attendees_list,
                'location': location,
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                        {'method': 'popup', 'minutes': 10},       # 10 minutes before
                    ],
                },
            }
            
            # Create the event
            event = self.service.events().insert(
                calendarId='primary',
                body=event_body,
                sendUpdates='all' if send_notifications else 'none'
            ).execute()
            
            event_link = event.get('htmlLink', 'No link available')
            event_id = event.get('id', 'Unknown ID')
            
            result = f"✅ Calendar event created successfully!\n"
            result += f"📅 Title: {title}\n"
            result += f"🕐 Time: {start_time.strftime('%Y-%m-%d %H:%M')} - {end_time.strftime('%Y-%m-%d %H:%M')}\n"
            if attendees:
                result += f"👥 Attendees: {', '.join(attendees)}\n"
            if location:
                result += f"📍 Location: {location}\n"
            result += f"🔗 Event Link: {event_link}\n"
            result += f"🆔 Event ID: {event_id}"
            
            self.logger.info(f"CALENDAR_TOOL :: Event created: {event_id}")
            return result
            
        except HttpError as e:
            error_msg = f"Google Calendar API error: {e}"
            self.logger.error(f"CALENDAR_TOOL :: {error_msg}")
            return f"❌ {error_msg}"
        except Exception as e:
            error_msg = f"Failed to create calendar event: {e}"
            self.logger.error(f"CALENDAR_TOOL :: {error_msg}")
            return f"❌ {error_msg}"

    #########################################################################################
    # List upcoming events from the calendar.
    #########################################################################################
    def list_upcoming_events(self, max_results: int = 10) -> str:
        """
        List upcoming events from the primary calendar.
        
        Args:
            max_results: Maximum number of events to return
            
        Returns:
            Formatted list of upcoming events
        """
        try:
            # Get current time
            now = datetime.utcnow().isoformat() + 'Z'
            
            # Call the Calendar API
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            if not events:
                return "📅 No upcoming events found."
            
            result = f"📅 Upcoming Events ({len(events)}):\n\n"
            
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                title = event.get('summary', 'No Title')
                attendees = event.get('attendees', [])
                location = event.get('location', '')
                event_id = event.get('id', '')
                
                # Format start time
                if 'T' in start:
                    start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    start_formatted = start_dt.strftime('%Y-%m-%d %H:%M')
                else:
                    start_formatted = start
                
                result += f"• {title}\n"
                result += f"  🕐 {start_formatted}\n"
                if location:
                    result += f"  📍 {location}\n"
                if attendees:
                    attendee_emails = [a.get('email', '') for a in attendees]
                    result += f"  👥 {', '.join(attendee_emails)}\n"
                result += f"  🆔 ID: {event_id}\n"
                result += "\n"
            
            return result
            
        except HttpError as e:
            error_msg = f"Google Calendar API error: {e}"
            self.logger.error(f"CALENDAR_TOOL :: {error_msg}")
            return f"❌ {error_msg}"
        except Exception as e:
            error_msg = f"Failed to list events: {e}"
            self.logger.error(f"CALENDAR_TOOL :: {error_msg}")
            return f"❌ {error_msg}"

    #########################################################################################
    # Delete a calendar event by ID.
    #########################################################################################
    def delete_event(self, event_id: str) -> str:
        """
        Delete a calendar event by its ID.
        
        Args:
            event_id: The ID of the event to delete
            
        Returns:
            Success or error message
        """
        try:
            self.service.events().delete(
                calendarId='primary',
                eventId=event_id
            ).execute()
            
            self.logger.info(f"CALENDAR_TOOL :: Event deleted: {event_id}")
            return f"✅ Event {event_id} deleted successfully."
            
        except HttpError as e:
            error_msg = f"Google Calendar API error: {e}"
            self.logger.error(f"CALENDAR_TOOL :: {error_msg}")
            return f"❌ {error_msg}"
        except Exception as e:
            error_msg = f"Failed to delete event: {e}"
            self.logger.error(f"CALENDAR_TOOL :: {error_msg}")
            return f"❌ {error_msg}"