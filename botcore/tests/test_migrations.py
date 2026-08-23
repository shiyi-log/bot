from datetime import timedelta

from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class TelegramLoginAccountPhoneMigrationTests(TransactionTestCase):
    migrate_from = [
        ("botcore", "0008_telegramloginaccount_botsettings_telegram_api_hash_and_more"),
    ]
    migrate_to = [
        ("botcore", "0009_secure_telegram_login_account_phone"),
    ]

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_from)
        old_apps = executor.loader.project_state(self.migrate_from).apps
        account_model = old_apps.get_model("botcore", "TelegramLoginAccount")
        now = timezone.now()

        donor = account_model.objects.create(
            label="Newest donor",
            phone="+1 (202) 555-0100",
            username="merged_username",
            status="pending",
        )
        winner = account_model.objects.create(
            label="Session winner",
            phone="+12025550100",
            username="",
            status="logged_in",
            session_string="fernet:fake-existing-session",
        )
        account_model.objects.create(
            label="International prefix duplicate",
            phone="0012025550100",
            first_name="Prefix",
            status="pending",
        )
        account_model.objects.filter(pk=donor.pk).update(updated_at=now)
        account_model.objects.filter(pk=winner.pk).update(updated_at=now - timedelta(days=1))
        account_model.objects.create(label="Blank", phone="")
        account_model.objects.create(label="Whitespace", phone="   ")
        self.winner_id = winner.pk

        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_to)
        self.apps = executor.loader.project_state(self.migrate_to).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_cleanup_keeps_best_account_merges_public_identity_and_adds_constraints(self):
        account_model = self.apps.get_model("botcore", "TelegramLoginAccount")
        accounts = list(account_model.objects.all())

        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0].pk, self.winner_id)
        self.assertEqual(accounts[0].phone, "+12025550100")
        self.assertEqual(accounts[0].username, "merged_username")
        self.assertEqual(accounts[0].first_name, "Prefix")
        self.assertEqual(accounts[0].status, "logged_in")
        self.assertTrue(accounts[0].session_string)

        with self.assertRaises(IntegrityError), transaction.atomic():
            account_model.objects.create(label="Duplicate", phone="+12025550100")
        with self.assertRaises(IntegrityError), transaction.atomic():
            account_model.objects.create(label="Blank", phone="")
