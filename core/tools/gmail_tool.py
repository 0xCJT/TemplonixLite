#########################################################################################
# Creates Gmail drafts via the Gmail API. Uses seperate OAuth credentials from the Calendar tool to preserve scope seperation. 
#########################################################################################
import base64
import logging
import os
from typing import Optional
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GmailTool:
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        # Only needs compose scope to create drafts (modify also works, compose is minimal)
        self.SCOPES = ['https://www.googleapis.com/auth/gmail.compose']
        self.service = self._get_gmail_service()

    def _get_gmail_service(self):
        creds = None
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        token_path = os.path.join(project_root, 'token_gmail.json')      # keep separate from Calendar
        credentials_path = os.path.join(project_root, 'credentials_gmail.json')

        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, self.SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    self.logger.info("GMAIL_TOOL :: Refreshing expired credentials...")
                    creds.refresh(Request())
                except Exception as e:
                    self.logger.error(f"GMAIL_TOOL :: Failed to refresh credentials: {e}")
                    creds = None

            if not creds:
                if not os.path.exists(credentials_path):
                    raise FileNotFoundError(
                        "credentials.json not found. Enable Gmail API in Google Cloud, then download OAuth client credentials to project root."
                    )
                try:
                    self.logger.info("GMAIL_TOOL :: Starting OAuth flow...")
                    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, self.SCOPES)
                    # console flow is reliable for headless environments
                    creds = flow.run_console()
                except Exception as e:
                    self.logger.error(f"GMAIL_TOOL :: Console OAuth failed: {e}")
                    self.logger.info("GMAIL_TOOL :: Trying local server flow...")
                    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, self.SCOPES)
                    creds = flow.run_local_server(port=8081, open_browser=True)

            # persist token
            try:
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
                self.logger.info("GMAIL_TOOL :: Credentials saved successfully")
            except Exception as e:
                self.logger.error(f"GMAIL_TOOL :: Failed to save credentials: {e}")

        return build('gmail', 'v1', credentials=creds)

    def _build_mime(
        self,
        from_address: Optional[str],
        to_address: str,
        subject: str,
        body: str,
        attachment_path: Optional[str] = None
    ) -> MIMEMultipart:
        message = MIMEMultipart()
        if from_address:
            message["From"] = from_address
        message["To"] = to_address
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        if attachment_path and attachment_path != "None":
            with open(attachment_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f'attachment; filename="{os.path.basename(attachment_path)}"'
                )
                message.attach(part)
        return message

    def create_draft(
        self,
        to_address: str,
        subject: str,
        body: str,
        attachment_path: Optional[str] = None,
        from_address_env: str = "GOOGLE_EMAIL_ADDRESS"
    ) -> str:
        """
        Create a Gmail draft in the user's Drafts folder.
        Returns a human-readable summary including the Draft ID.
        """
        try:
            from_address = os.getenv(from_address_env, None)
            mime_msg = self._build_mime(from_address, to_address, subject, body, attachment_path)

            raw = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode("utf-8")
            draft_body = {"message": {"raw": raw}}

            draft = self.service.users().drafts().create(userId="me", body=draft_body).execute()
            draft_id = draft.get("id", "unknown")
            thread_id = draft.get("message", {}).get("threadId", "unknown")

            summary = [
                "Draft created successfully in Gmail.",
                f"Draft ID: {draft_id}",
                f"Thread ID: {thread_id}",
                f"To: {to_address}",
                f"Subject: {subject}",
            ]
            if attachment_path and attachment_path != "None":
                summary.append(f"📎 Attachment: {os.path.basename(attachment_path)}")

            return "\n".join(summary)
        except HttpError as e:
            self.logger.error(f"GMAIL_TOOL :: Gmail API error: {e}")
            return f"Gmail API error: {e}"
        except Exception as e:
            self.logger.error(f"GMAIL_TOOL :: Failed to create draft: {e}")
            return f"Failed to create draft: {e}"