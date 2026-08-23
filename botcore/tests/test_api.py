from django.test import TestCase
from rest_framework.test import APIClient

from botcore.models import TelegramBot, TelegramGroup, TelegramGroupMember, TelegramUser

VALID_ADDRESS = "T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb"


class ApiContractTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_settings_get_and_patch(self):
        response = self.client.get("/api/settings/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["tron_api_url"], "https://api.trongrid.io")
        self.assertEqual(response.data["tron_api_key_env_var"], "TRONGRID_API_KEY")
        self.assertFalse(response.data["tron_api_key_configured"])
        self.assertNotIn("tron_api_key", response.data)
        response = self.client.patch("/api/settings/", {
            "tron_api_key": "alpha-secret,beta-secret",
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("tron_api_key", response.data)
        self.assertEqual(response.data["tron_api_key_preview"], "alp***ret")
        self.assertTrue(response.data["tron_api_key_configured"])
        response = self.client.patch("/api/settings/", {
            "tron_api_url": "https://api.example.test/tron/",
            "tron_api_key_env_var": "CUSTOM_TRON_KEY",
            "tron_poll_interval": 45,
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["tron_api_url"], "https://api.example.test/tron")
        self.assertEqual(response.data["tron_api_key_env_var"], "CUSTOM_TRON_KEY")
        self.assertEqual(response.data["tron_poll_interval"], 45)
        self.assertNotIn("welcome_message", response.data)

        invalid = self.client.patch("/api/settings/", {
            "tron_api_key_env_var": "not-a-valid-name",
        }, format="json")
        self.assertEqual(invalid.status_code, 400)

    def test_user_filter_group_list_and_dashboard(self):
        TelegramUser.objects.create(telegram_id=10, username="active", is_active=True)
        TelegramUser.objects.create(telegram_id=11, username="disabled", is_active=False)
        TelegramGroup.objects.create(telegram_id=-10, title="Test", group_type="group")
        users = self.client.get("/api/users/", {"is_active": "true"})
        self.assertEqual(users.status_code, 200)
        self.assertEqual(users.data["count"], 1)
        self.assertEqual(self.client.get("/api/groups/").data["count"], 1)
        summary = self.client.get("/api/dashboard/summary/")
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.data["telegram_users"], 2)
        self.assertEqual(summary.data["telegram_groups"], 1)

    def test_tron_address_crud_and_validation(self):
        created = self.client.post("/api/tron/addresses/", {"address": VALID_ADDRESS, "label": "Treasury"}, format="json")
        self.assertEqual(created.status_code, 201)
        address_id = created.data["id"]
        patched = self.client.patch(f"/api/tron/addresses/{address_id}/", {"enabled": False}, format="json")
        self.assertEqual(patched.status_code, 200)
        self.assertFalse(patched.data["enabled"])
        invalid = self.client.post("/api/tron/addresses/", {"address": "T" + "x" * 33}, format="json")
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(self.client.delete(f"/api/tron/addresses/{address_id}/").status_code, 204)

    def test_group_member_list_can_be_filtered_by_group(self):
        user = TelegramUser.objects.create(telegram_id=100, username="speaker")
        group = TelegramGroup.objects.create(telegram_id=-100, title="Group", group_type="supergroup")
        bot = TelegramBot.objects.create(name="Main", token_env_var="MAIN_BOT_TOKEN")
        TelegramGroupMember.objects.create(
            bot=bot,
            group=group,
            user=user,
            username="speaker",
            first_name="Speaker",
            message_count=3,
        )

        response = self.client.get("/api/members/", {"group": group.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["telegram_user_id"], 100)
        self.assertEqual(response.data["results"][0]["group_telegram_id"], -100)
        self.assertEqual(response.data["results"][0]["bot_name"], "Main")

        groups = self.client.get("/api/groups/")
        self.assertEqual(groups.data["results"][0]["member_count"], 1)

    def test_bot_and_button_crud_do_not_expose_token_values(self):
        created = self.client.post("/api/bots/", {
            "name": "Support",
            "token_env_var": "SUPPORT_BOT_TOKEN",
            "enabled": True,
            "welcome_message": "Hi {first_name}",
        }, format="json")
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["button_count"], 0)
        self.assertNotIn("token", created.data)
        self.assertEqual(created.data["token_env_var"], "SUPPORT_BOT_TOKEN")

        button = self.client.post("/api/bot-buttons/", {
            "bot": created.data["id"],
            "text": "Help",
            "url": "https://example.com/help",
            "row": 1,
            "position": 1,
            "enabled": True,
        }, format="json")
        self.assertEqual(button.status_code, 201)
        listed = self.client.get("/api/bot-buttons/", {"bot": created.data["id"]})
        self.assertEqual(listed.data["count"], 1)
        self.assertEqual(listed.data["results"][0]["text"], "Help")

    def test_bot_clone_copies_safe_configuration_and_buttons(self):
        source = TelegramBot.objects.create(
            name="Main",
            token_env_var="MAIN_BOT_TOKEN",
            enabled=True,
            welcome_enabled=False,
            welcome_message="Hello {first_name}",
        )
        TelegramBot.objects.get(pk=source.pk).buttons.create(
            text="Help", url="https://example.com/help", row=1, position=1,
        )

        response = self.client.post(
            f"/api/bots/{source.pk}/clone/",
            {"billing_plan": "pro"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        clone = TelegramBot.objects.get(pk=response.data["id"])
        self.assertEqual(clone.cloned_from_id, source.pk)
        self.assertEqual(clone.welcome_message, source.welcome_message)
        self.assertFalse(clone.enabled)
        self.assertIsNone(clone.telegram_id)
        self.assertNotEqual(clone.token_env_var, source.token_env_var)
        self.assertEqual(clone.buttons.count(), 1)
        self.assertEqual(response.data["billing"]["status"], "reserved")
        self.assertEqual(response.data["billing"]["plan"], "pro")

    def test_bot_clone_respects_clone_enabled(self):
        source = TelegramBot.objects.create(
            name="Private", token_env_var="PRIVATE_BOT_TOKEN", clone_enabled=False,
        )
        count_before = TelegramBot.objects.count()
        response = self.client.post(f"/api/bots/{source.pk}/clone/", {}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(TelegramBot.objects.count(), count_before)
