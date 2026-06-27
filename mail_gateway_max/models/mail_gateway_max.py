# Copyright 2026 ЧОУ СПБГШ 'РОСТ'
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import logging
import traceback
from io import StringIO

import requests

from odoo import _, api, models
from odoo.http import request
from odoo.tools import html2plaintext

from odoo.addons.base.models.ir_mail_server import MailDeliveryException

_logger = logging.getLogger(__name__)

_DEFAULT_MAX_API_BASE = "https://platform-api.max.ru"


def _get_max_api_base(env):
    """Get MAX API base URL from system parameter, fallback to default."""
    return env["ir.config_parameter"].sudo().get_param(
        "mail_gateway_max.api_base_url", _DEFAULT_MAX_API_BASE
    )


class MailGatewayMaxService(models.AbstractModel):
    _inherit = "mail.gateway.abstract"
    _name = "mail.gateway.max"
    _description = "MAX Gateway services"

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _max_headers(self, gateway):
        return {
            "Authorization": gateway.token,
            "Content-Type": "application/json",
        }

    def _max_request(self, gateway, method, path, **kwargs):
        """Low-level HTTP call to MAX API. Returns response JSON or None."""
        base = _get_max_api_base(self.env)
        url = f"{base}{path}"
        headers = self._max_headers(gateway)
        try:
            res = requests.request(
                method, url, headers=headers, timeout=15, **kwargs
            )
            if res.ok:
                return res.json()
            _logger.warning(
                "MAX API %s %s returned %s: %s",
                method, path, res.status_code, res.text[:500],
            )
        except requests.RequestException as exc:
            _logger.error("MAX API request failed: %s", exc)
        return None

    # ------------------------------------------------------------------
    # Webhook management
    # ------------------------------------------------------------------

    def _set_webhook(self, gateway):
        """Register webhook on MAX platform."""
        payload = {
            "url": gateway.webhook_url,
        }
        if gateway.webhook_secret:
            payload["secret"] = gateway.webhook_secret
        result = self._max_request(gateway, "POST", "/subscriptions", json=payload)
        if result is not None:
            _logger.info("MAX webhook set for gateway %s", gateway.name)
        else:
            _logger.warning("Failed to set MAX webhook for %s", gateway.name)
        return super()._set_webhook(gateway)

    def _remove_webhook(self, gateway):
        """Remove webhook from MAX platform."""
        result = self._max_request(gateway, "DELETE", "/subscriptions")
        if result is not None:
            _logger.info("MAX webhook removed for %s", gateway.name)
        return super()._remove_webhook(gateway)

    # ------------------------------------------------------------------
    # Update verification
    # ------------------------------------------------------------------

    def _verify_update(self, bot_data, kwargs):
        """Verify incoming webhook request using secret token header."""
        if not bot_data.get("webhook_secret"):
            return True
        secret = request.httprequest.headers.get("X-Max-Signature")
        if not secret:
            secret = request.httprequest.headers.get("X-Max-Secret-Token")
        return secret == bot_data["webhook_secret"]

    # ------------------------------------------------------------------
    # Incoming message handling
    # ------------------------------------------------------------------

    def _get_channel_vals(self, gateway, token, update):
        result = super()._get_channel_vals(gateway, token, update)
        # Extract chat name from update
        message = update.get("message") or update
        sender = message.get("sender", {})
        name = sender.get("name") or sender.get("first_name", "") + " " + sender.get("last_name", "")
        name = name.strip() or "MAX Chat"
        result["name"] = name
        result["anonymous_name"] = name
        return result

    def _receive_update(self, gateway, update):
        """Process incoming webhook update from MAX."""
        # Parse the incoming message
        message = update.get("message") or update
        if not message:
            _logger.warning("MAX update without message: %s", update)
            return

        # Extract chat_id from sender (used as channel token for replies)
        sender = message.get("sender", {})
        chat_id = str(sender.get("user_id", ""))
        if not chat_id:
            _logger.warning("MAX update without sender.user_id: %s", message)
            return

        # Get or create discuss channel
        chat = self._get_channel(gateway, chat_id, update)
        if not chat:
            return

        # Extract body text from message.body.text
        body_data = message.get("body", {})
        body = body_data.get("text", "") or ""
        attachments = []

        author = self._get_author(gateway, message)
        author_id = False
        if author:
            author_id = author._name == "res.partner" and author.id
        new_message = chat.message_post(
            body=body,
            author_id=author_id,
            gateway_type="max",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
            attachments=attachments,
        )
        self._post_process_message(new_message, chat)
        return new_message

    # ------------------------------------------------------------------
    # Author / Guest resolution
    # ------------------------------------------------------------------

    def _get_author_vals(self, gateway, message):
        sender = message.get("sender", {})
        name = sender.get("name", "") or (sender.get("first_name", "") + " " + sender.get("last_name", "")).strip() or "MAX User"
        user_id = str(sender.get("user_id", ""))
        return {
            "name": name,
            "gateway_id": gateway.id,
            "gateway_token": user_id,
        }

    def _get_author(self, gateway, message):
        sender = message.get("sender", {})
        user_id = sender.get("user_id")
        if not user_id:
            # Fallback: use recipient's chat_id as author token
            recipient = message.get("recipient", {})
            user_id = str(recipient.get("chat_id", ""))
            if not user_id:
                return False
            sender = {
                "user_id": user_id,
                "name": "Bot",
            }

        # Check existing partner gateway channel
        gateway_partner = self.env["res.partner.gateway.channel"].search(
            [
                ("gateway_id", "=", gateway.id),
                ("gateway_token", "=", str(user_id)),
            ]
        )
        if gateway_partner:
            return gateway_partner.partner_id

        # Check existing guest
        guest = self.env["mail.guest"].search(
            [
                ("gateway_id", "=", gateway.id),
                ("gateway_token", "=", str(user_id)),
            ]
        )
        if guest:
            return guest

        # Create new guest
        return self.env["mail.guest"].create(
            self._get_author_vals(gateway, message)
        )

    # ------------------------------------------------------------------
    # Outbound message sending
    # ------------------------------------------------------------------

    def _send(
        self,
        gateway,
        record,
        auto_commit=False,
        raise_exception=False,
        parse_mode=False,
    ):
        """Send a message to MAX via the API."""
        message_text = self._get_message_body(record)
        if not message_text:
            _logger.warning("MAX send: empty body for record %s", record.id)
            return

        chat_id = record.gateway_channel_id.gateway_channel_token
        if not chat_id:
            _logger.warning("MAX send: no chat_id for record %s", record.id)
            return

        payload = {
            "text": html2plaintext(message_text),
        }
        if parse_mode:
            payload["format"] = "html" if parse_mode in ("HTML", "html") else parse_mode

        try:
            result = self._max_request(
                gateway, "POST", "/messages?user_id=" + chat_id, json=payload
            )
            if result is None:
                raise Exception("MAX API returned error")

            record.sudo().write(
                {
                    "notification_status": "sent",
                    "failure_reason": False,
                    "failure_type": False,
                    "gateway_message_id": result.get("message_id"),
                }
            )

        except Exception as exc:
            buff = StringIO()
            traceback.print_exc(file=buff)
            _logger.error(buff.getvalue())
            if raise_exception:
                raise MailDeliveryException(
                    _("Unable to send the MAX message"), exc
                ) from None
            else:
                _logger.warning(
                    "Issue sending MAX message id %s: %s", record.id, exc
                )
                record.sudo().write(
                    {
                        "notification_status": "exception",
                        "failure_reason": exc,
                        "failure_type": "unknown",
                    }
                )

        self.env["bus.bus"]._sendone(
            record.gateway_channel_id,
            "mail.message/insert",
            {
                "id": record.mail_message_id.id,
                "gateway_type": record.mail_message_id.gateway_type,
            },
        )

        if auto_commit is True:
            self.env.cr.commit()
