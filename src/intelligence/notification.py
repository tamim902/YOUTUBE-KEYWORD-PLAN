"""Optional Email and Webhook Notification Dispatcher (Phase 22 Part 10).

Provides secure, opt-in morning digest notifications via:
- SMTP Email (TLS/SSL with recipient and subject)
- HTTP Webhook (Discord / Slack / Generic JSON POST)

Honest disclosure: If notification settings are not configured or empty,
delivery is safely skipped with a clear log rather than failing or claiming sent.
"""

import json
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Tuple
from urllib.request import Request, urlopen

from src.models.morning_report import DailyMorningReport

logger = logging.getLogger(__name__)


class NotificationService:
    """Dispatches daily reports via SMTP or Webhook when explicitly configured."""

    def __init__(self) -> None:
        pass

    def dispatch_report(
        self,
        report: DailyMorningReport,
        smtp_config: Optional[Dict[str, Any]] = None,
        webhook_url: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Attempt to deliver the report digest to configured notification channels.
        
        Returns:
            (success, message)
        """
        messages: List[str] = []
        any_configured = False

        # 1. SMTP Delivery
        if smtp_config and smtp_config.get("host") and smtp_config.get("to_email"):
            any_configured = True
            ok, msg = self._send_smtp_email(report, smtp_config)
            messages.append(msg)
        
        # 2. Webhook Delivery
        if webhook_url and webhook_url.strip().startswith("http"):
            any_configured = True
            ok, msg = self._send_webhook(report, webhook_url.strip())
            messages.append(msg)

        if not any_configured:
            return (
                True,
                "Notification delivery skipped: Neither SMTP credentials nor Webhook URL are configured. Morning digest is saved in local dashboard.",
            )

        return True, " | ".join(messages)

    def _send_smtp_email(self, report: DailyMorningReport, config: Dict[str, Any]) -> Tuple[bool, str]:
        """Send formatted HTML/Text email digest via SMTP."""
        host = config.get("host", "")
        port = int(config.get("port", 587))
        username = config.get("username", "")
        password = config.get("password", "")
        from_email = config.get("from_email", username)
        to_email = config.get("to_email", "")

        subject = f"🌅 Keyword Studio Daily Morning Report — {report.run_date} ({len(report.ideas)} Ideas Across 4 Channels)"
        
        # Build plain text body
        lines = [
            f"KEYWORD STUDIO DAILY MORNING REPORT",
            f"Date: {report.run_date} ({report.timezone_name})",
            f"Total Ideas: {len(report.ideas)}",
            "=" * 60,
            "",
        ]
        
        # Group ideas by channel
        for channel_id in [1, 2, 3, 4]:
            channel_ideas = [i for i in report.ideas if i.channel_id == channel_id]
            if channel_ideas:
                chan_name = channel_ideas[0].channel_name
                lines.append(f"\n📺 CHANNEL {channel_id}: {chan_name.upper()}")
                lines.append("-" * 40)
                for idx, idea in enumerate(channel_ideas, 1):
                    lines.append(f"{idx}. {idea.proposed_topic}")
                    lines.append(f"   Keyword: {idea.main_keyword} | Intent: {idea.search_intent}")
                    lines.append(f"   Gap State: {idea.gap_state} ({idea.recent_relevant_videos_found} recent videos)")
                    lines.append(f"   Score: {idea.opportunity_estimate}/100 | Format: {idea.suggested_video_format}")
                    lines.append(f"   Recommended: {idea.next_recommended_action}")
                    lines.append("")

        body_text = "\n".join(lines)

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = from_email
            msg["To"] = to_email
            msg.attach(MIMEText(body_text, "plain", "utf-8"))

            with smtplib.SMTP(host, port, timeout=10) as server:
                server.starttls()
                if username and password:
                    server.login(username, password)
                server.sendmail(from_email, [to_email], msg.as_string())
            return True, f"Email digest successfully sent to {to_email}"
        except Exception as e:
            logger.warning(f"Failed to send SMTP email: {e}")
            return False, f"SMTP delivery failed: {str(e)}"

    def _send_webhook(self, report: DailyMorningReport, webhook_url: str) -> Tuple[bool, str]:
        """Post summary JSON payload to configured webhook."""
        payload = {
            "content": f"🌅 **Keyword Studio Daily Morning Report — {report.run_date}**\nGenerated **{len(report.ideas)} new video ideas** across 4 configured YouTube channels.",
            "embeds": [
                {
                    "title": f"Daily Idea Summary — {report.run_date}",
                    "description": f"Processed 4 channels in timezone `{report.timezone_name}`.\nStatus: `{report.status}`",
                    "fields": [
                        {
                            "name": f"Channel {c_id}: {ideas[0].channel_name}",
                            "value": "\n".join([f"• **{i.proposed_topic}** ({i.gap_state}, Score: {i.opportunity_estimate})" for i in ideas[:3]]),
                            "inline": False,
                        }
                        for c_id in [1, 2, 3, 4]
                        for ideas in [[i for i in report.ideas if i.channel_id == c_id]]
                        if ideas
                    ],
                }
            ],
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = Request(webhook_url, data=data, headers={"Content-Type": "application/json", "User-Agent": "KeywordStudio/22.0"})
            with urlopen(req, timeout=10) as resp:
                code = resp.getcode()
                if 200 <= code < 300:
                    return True, f"Webhook notification delivered (HTTP {code})"
                return False, f"Webhook returned HTTP {code}"
        except Exception as e:
            logger.warning(f"Failed to post webhook: {e}")
            return False, f"Webhook delivery failed: {str(e)}"


# Default singleton instance
notification_service = NotificationService()
