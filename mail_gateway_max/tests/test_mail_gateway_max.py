"""Tests for mail_gateway_max."""

from odoo.tests import TransactionCase


class TestMailGatewayMax(TransactionCase):
    """Basic test cases for MAX gateway."""

    def setUp(self):
        super().setUp()
        self.gateway = self.env["mail.gateway"].create(
            {
                "name": "Test MAX Bot",
                "token": "test_token_123",
                "gateway_type": "max",
                "webhook_key": "test_key",
                "webhook_secret": "test_secret",
            }
        )

    def test_gateway_type_selection(self):
        """Test that 'max' type is available in gateway."""
        self.assertEqual(self.gateway.gateway_type, "max")

    def test_max_chat_model(self):
        """Test creation of max.chat records."""
        chat = self.env["max.chat"].create(
            {
                "name": "Test Chat",
                "chat_id": "12345",
                "gateway_id": self.gateway.id,
            }
        )
        self.assertEqual(chat.name, "Test Chat")
        self.assertEqual(chat.chat_id, "12345")
        self.assertEqual(chat.gateway_id, self.gateway)

    def test_service_class_exists(self):
        """Test that the service class is registered."""
        service = self.env["mail.gateway.max"]
        self.assertTrue(service is not None)

    def test_send_wrong_type(self):
        """Test that send_message returns False for non-max gateways."""
        self.gateway.gateway_type = "telegram"
        result = self.gateway.send_message("12345", "test")
        self.assertFalse(result)
