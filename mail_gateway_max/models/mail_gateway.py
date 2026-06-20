# Copyright 2026 ЧОУ СПБГШ 'РОСТ'
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

import requests

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

MAX_API_BASE = "https://platform-api.max.ru"


def _get_max_api_base(env):
    """Get MAX API base URL from system parameter, fallback to default."""
    return env["ir.config_parameter"].sudo().get_param(
        "mail_gateway_max.api_base_url", MAX_API_BASE
    )


class MailGateway(models.Model):
    _inherit = "mail.gateway"

    gateway_type = fields.Selection(
        selection_add=[("max", "MAX")], ondelete={"max": "cascade"}
    )

    max_chat_ids = fields.One2many(
        "max.chat", "gateway_id", string="Authorized Chats"
    )

    # ------------------------------------------------------------------
    # Direct API helpers
    # ------------------------------------------------------------------

    def _max_headers_standalone(self):
        return {
            "Authorization": self.token,
            "Content-Type": "application/json",
        }

    def send_message(self, chat_id, message, parse_mode="HTML"):
        """Low-level method to send a raw message via MAX API."""
        self.ensure_one()
        if self.gateway_type != "max":
            return False

        # Whitelist check
        if self.max_chat_ids:
            if not self.max_chat_ids.filtered(
                lambda c, cid=chat_id: c.chat_id == str(cid)
            ):
                _logger.warning(
                    "MAX bot %s: chat_id %s is not in authorized list, skipping",
                    self.name, chat_id,
                )
                return False

        base = _get_max_api_base(self.env)
        url = f"{base}/messages"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": parse_mode,
        }
        try:
            with requests.Session() as session:
                response = session.post(
                    url,
                    json=payload,
                    headers=self._max_headers_standalone(),
                    timeout=10,
                )
                response.raise_for_status()
            return True
        except Exception as e:
            _logger.error("MAX error for bot %s: %s", self.name, e)
            return False

    def action_test_connection(self):
        """Button to test connection — sends test message to all registered chats."""
        self.ensure_one()
        if self.gateway_type != "max":
            return False

        if not self.max_chat_ids:
            raise UserError(_("Please add or fetch at least one Chat ID first."))

        for chat in self.max_chat_ids:
            msg = (
                _("<b>Success!</b> Connection from Odoo to <i>%s</i> is working.")
                % self.name
            )
            self.send_message(chat.chat_id, msg)

        return {
            "effect": {
                "fadeout": "slow",
                "message": _("Test messages sent!"),
                "type": "rainbow_man",
            }
        }

    def _is_webhook_active(self):
        """Check via MAX API if a webhook is currently set."""
        self.ensure_one()
        if self.gateway_type != "max":
            return super()._is_webhook_active()
        try:
            base = _get_max_api_base(self.env)
            url = f"{base}/subscriptions"
            response = requests.get(
                url,
                headers=self._max_headers_standalone(),
                timeout=10,
            )
            if response.ok:
                data = response.json()
                if data.get("url"):
                    return True
            return False
        except Exception:
            return False

    def action_fetch_chats(self):
        """Discover chat IDs via MAX getUpdates."""
        self.ensure_one()
        if self.gateway_type != "max":
            return False

        if self._is_webhook_active():
            raise UserError(
                _(
                    "MAX does not allow fetching updates manually "
                    "while a Webhook is active. "
                    "Please disable the Webhook before using 'Fetch Chats'."
                )
            )

        try:
            base = _get_max_api_base(self.env)
            url = f"{base}/updates"
            response = requests.get(
                url,
                headers=self._max_headers_standalone(),
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            updates = data if isinstance(data, list) else data.get("result", [])

            for update in updates:
                message = update.get("message") or update.get("edited_message") or update
                chat_info = message.get("chat", {})
                if not chat_info.get("id"):
                    continue

                c_id = str(chat_info["id"])
                c_name = (
                    chat_info.get("title")
                    or chat_info.get("name")
                    or chat_info.get("username")
                    or "Unknown"
                )

                if not self.max_chat_ids.filtered(
                    lambda c, c_id=c_id: c.chat_id == c_id
                ):
                    self.env["max.chat"].create(
                        {
                            "name": c_name,
                            "chat_id": c_id,
                            "gateway_id": self.id,
                        }
                    )
            return True
        except Exception as e:
            _logger.error("Fetch failed: %s", e)
            return False
