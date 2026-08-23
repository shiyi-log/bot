from django.test import TestCase, override_settings

from botcore.crypto import decrypt_text, encrypt_text
from botcore.models import BotSettings, TelegramLoginAccount


@override_settings(SECRET_KEY="fake-test-secret", CONFIG_ENCRYPTION_KEY="fake-config-key")
class CryptoTests(TestCase):
    def test_encrypt_and_decrypt_round_trip(self):
        plaintext = "fake-sensitive-value"

        encrypted = encrypt_text(plaintext)

        self.assertTrue(encrypted.startswith("fernet:"))
        self.assertNotIn(plaintext, encrypted)
        self.assertEqual(decrypt_text(encrypted), plaintext)
        self.assertEqual(encrypt_text(""), "")
        self.assertEqual(decrypt_text(""), "")

    def test_invalid_fernet_value_returns_empty_string(self):
        invalid_value = "fernet:not-a-valid-token"

        self.assertEqual(decrypt_text(invalid_value), "")

    def test_plaintext_value_is_rejected_by_default(self):
        self.assertEqual(decrypt_text("fake-plaintext-value"), "")

    def test_legacy_plaintext_value_requires_explicit_opt_in(self):
        legacy_value = "fake-legacy-value"

        self.assertEqual(decrypt_text(legacy_value, allow_plaintext=True), legacy_value)

    def test_config_encryption_key_takes_precedence_over_secret_key(self):
        with self.settings(SECRET_KEY="fake-secret-one", CONFIG_ENCRYPTION_KEY="fake-config-key"):
            encrypted = encrypt_text("fake-sensitive-value")

        with self.settings(SECRET_KEY="fake-secret-two", CONFIG_ENCRYPTION_KEY="fake-config-key"):
            self.assertEqual(decrypt_text(encrypted), "fake-sensitive-value")

        with self.settings(SECRET_KEY="fake-secret-one", CONFIG_ENCRYPTION_KEY="fake-other-config-key"):
            self.assertEqual(decrypt_text(encrypted), "")

    def test_secret_key_is_used_when_config_encryption_key_is_missing(self):
        with self.settings(SECRET_KEY="fake-fallback-secret", CONFIG_ENCRYPTION_KEY=None):
            encrypted = encrypt_text("fake-sensitive-value")
            self.assertEqual(decrypt_text(encrypted), "fake-sensitive-value")

        with self.settings(SECRET_KEY="fake-other-secret", CONFIG_ENCRYPTION_KEY=None):
            self.assertEqual(decrypt_text(encrypted), "")


@override_settings(SECRET_KEY="fake-test-secret", CONFIG_ENCRYPTION_KEY="fake-config-key")
class TelegramAccountModelTests(TestCase):
    def test_sensitive_fields_are_encrypted_and_plain_properties_restore_them(self):
        phone_code_hash = "fake-phone-code-hash"
        session_string = "fake-session-string"

        account = TelegramLoginAccount.objects.create(
            label="Fake account",
            phone="+10000000000",
            phone_code_hash=phone_code_hash,
            session_string=session_string,
        )

        account.refresh_from_db()
        self.assertTrue(account.phone_code_hash.startswith("fernet:"))
        self.assertTrue(account.session_string.startswith("fernet:"))
        self.assertNotIn(phone_code_hash, account.phone_code_hash)
        self.assertNotIn(session_string, account.session_string)
        self.assertEqual(account.phone_code_hash_plain, phone_code_hash)
        self.assertEqual(account.session_string_plain, session_string)
        self.assertEqual(account.status, TelegramLoginAccount.Status.PENDING)

    def test_saving_an_encrypted_account_does_not_double_encrypt(self):
        account = TelegramLoginAccount.objects.create(
            label="Fake account",
            phone="+10000000000",
            session_string="fake-session-string",
        )
        encrypted_session = account.session_string

        account.label = "Renamed fake account"
        account.save()
        account.refresh_from_db()

        self.assertEqual(account.session_string, encrypted_session)
        self.assertEqual(account.session_string_plain, "fake-session-string")

    def test_plain_properties_reject_bulk_updated_plaintext(self):
        account = TelegramLoginAccount.objects.create(
            label="Fake account",
            phone="+10000000000",
        )

        TelegramLoginAccount.objects.filter(pk=account.pk).update(
            phone_code_hash="fake-unencrypted-phone-code-hash",
            session_string="fake-unencrypted-session-string",
        )
        account.refresh_from_db()

        self.assertEqual(account.phone_code_hash_plain, "")
        self.assertEqual(account.session_string_plain, "")

    def test_telegram_api_hash_is_encrypted_but_tron_key_remains_plaintext(self):
        telegram_api_hash = "fake-telegram-api-hash"
        tron_api_key = "fake-tron-api-key"

        settings = BotSettings.objects.create(
            telegram_api_id="123456",
            telegram_api_hash=telegram_api_hash,
            tron_api_key=tron_api_key,
        )

        settings.refresh_from_db()
        self.assertEqual(settings.telegram_api_id, "123456")
        self.assertTrue(settings.telegram_api_hash.startswith("fernet:"))
        self.assertNotIn(telegram_api_hash, settings.telegram_api_hash)
        self.assertEqual(settings.telegram_api_hash_plain, telegram_api_hash)
        self.assertEqual(settings.tron_api_key, tron_api_key)

    def test_saving_bot_settings_does_not_double_encrypt_api_hash(self):
        settings = BotSettings.objects.create(
            telegram_api_hash="fake-telegram-api-hash",
        )
        encrypted_api_hash = settings.telegram_api_hash

        settings.tron_poll_interval = 45
        settings.save()
        settings.refresh_from_db()

        self.assertEqual(settings.telegram_api_hash, encrypted_api_hash)
        self.assertEqual(settings.telegram_api_hash_plain, "fake-telegram-api-hash")
