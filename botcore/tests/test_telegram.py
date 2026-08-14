from django.test import TestCase

from botcore.models import BotSettings, TelegramGroup, TelegramUser
from botcore.services.telegram import handle_update


class FakeTransport:
    def __init__(self):
        self.messages = []

    def send_message(self, chat_id, text):
        self.messages.append((chat_id, text))


class TelegramUpdateTests(TestCase):
    def setUp(self):
        self.transport = FakeTransport()

    def test_first_private_interaction_persists_user_and_welcomes(self):
        result = handle_update({"message": {
            "from": {"id": 42, "first_name": "Alice", "username": "alice", "is_bot": False},
            "chat": {"id": 42, "type": "private"},
            "text": "hello",
        }}, self.transport)
        self.assertEqual(result.user_id, 42)
        self.assertTrue(TelegramUser.objects.filter(telegram_id=42).exists())
        self.assertEqual(len(self.transport.messages), 1)
        self.assertIn("Alice", self.transport.messages[0][1])

        handle_update({"message": {
            "from": {"id": 42, "first_name": "Alice", "is_bot": False},
            "chat": {"id": 42, "type": "private"},
            "text": "again",
        }}, self.transport)
        self.assertEqual(len(self.transport.messages), 1)

    def test_id_and_chatid_commands(self):
        base = {
            "from": {"id": 99, "first_name": "User", "is_bot": False},
            "chat": {"id": -100123, "type": "supergroup", "title": "Ops"},
        }
        handle_update({"message": {**base, "text": "/id@sample_bot"}}, self.transport)
        handle_update({"message": {**base, "text": "/chatid"}}, self.transport)
        self.assertEqual(self.transport.messages, [
            (-100123, "用户 ID: 99"),
            (-100123, "群组 ID: -100123"),
        ])
        self.assertTrue(TelegramGroup.objects.filter(telegram_id=-100123).exists())

    def test_new_member_welcome_uses_configured_template(self):
        settings = BotSettings.load()
        settings.welcome_message = "Hi {first_name}, welcome to {group_title}"
        settings.save()
        handle_update({"message": {
            "from": {"id": 1, "first_name": "Admin", "is_bot": False},
            "chat": {"id": -7, "type": "group", "title": "Team"},
            "new_chat_members": [{"id": 2, "first_name": "Bob", "is_bot": False}],
        }}, self.transport)
        self.assertIn((-7, "Hi Bob, welcome to Team"), self.transport.messages)
        self.assertTrue(TelegramUser.objects.filter(telegram_id=2).exists())

    def test_start_command_sends_welcome_message(self):
        handle_update({"message": {
            "from": {"id": 7, "first_name": "Starter", "is_bot": False},
            "chat": {"id": 7, "type": "private"},
            "text": "/start",
        }}, self.transport)
        self.assertEqual(len(self.transport.messages), 1)
        self.assertIn("Starter", self.transport.messages[0][1])
