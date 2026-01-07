import logging
import os
import smtplib
import ssl
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

# Settings removed - using simple config objects


class EmailTool:
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.tool_name = "EMAIL_TOOL"

        # Load SMTP credentials from settings
        self.from_address = os.getenv("GOOGLE_EMAIL_ADDRESS")
        self.email_password = os.getenv("GOOGLE_EMAIL_PSWD") 
        self.smtp_server =  os.getenv("GOOGLE_EMAIL_SMTP_SERVER", "smtp.gmail.com")
        self.mail_port = int(os.getenv("GOOGLE_EMAIL_MAIL_PORT", "587"))
                
    #####################################################################################
    # Public method for MCP integration
    #####################################################################################
    def send_email(
        self,
        to_address: str,
        subject: str,
        body: str,
        attachment_path: Optional[str] = None,
    ) -> str:
        """Public method for sending emails via MCP"""
        return self._send_email(to_address, subject, body, attachment_path)

    #####################################################################################
    # Core SMTP logic to send the message with optional attachment.
    #####################################################################################
    def _send_email(
        self,
        to_address: str,
        subject: str,
        body: str,
        attachment_path: Optional[str] = None,
    ) -> str:
        try:
            message = MIMEMultipart()
            message["From"] = self.from_address
            message["To"] = to_address
            message["Subject"] = subject
            message.attach(MIMEText(body, "plain"))

            # Attach file if applicable
            if attachment_path and attachment_path != "None":
                with open(attachment_path, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={os.path.basename(attachment_path)}",
                    )
                    message.attach(part)

            context = ssl.create_default_context()

            with smtplib.SMTP(self.smtp_server, self.mail_port) as server:
                server.starttls(context=context)
                server.login(self.from_address, self.email_password)
                server.sendmail(self.from_address, to_address, message.as_string())

            return f"Email sent successfully to {to_address}. Please check your inbox."

        except Exception as e:
            self.logger.error(f"EMAIL_TOOL :: Failed to send email: {e}")
            return f"Failed to send email: {e}"