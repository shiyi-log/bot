from django.test import TestCase
from rest_framework.test import APIClient

from botcore.models import TelegramGroup, TelegramGroupMember, TelegramUser

VALID_ADDRESS = "T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb"


class ApiContractTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_settings_get_and_patch(self):
        response = self.client.get("/api/settings/")
        self.assertEqual(response.status_code, 200)
        response = self.client.patch("/api/settings/", {"welcome_message": "Welcome {first_name}"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["welcome_message"], "Welcome {first_name}")

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
        TelegramGroupMember.objects.create(
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

        groups = self.client.get("/api/groups/")
        self.assertEqual(groups.data["results"][0]["member_count"], 1)
