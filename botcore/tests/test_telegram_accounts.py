import asyncio
import os
import traceback
from dataclasses import dataclass
from unittest.mock import patch

from django.test import TestCase, override_settings
from telethon import errors

from botcore.crypto import decrypt_text, encrypt_text
from botcore.models import BotSettings, TelegramLoginAccount
from botcore.services.telegram_accounts import (
    TelegramAccountError,
    check_session,
    create_telegram_client,
    normalize_phone,
    send_login_code,
    sign_in_with_code,
    sign_in_with_password,
)


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


@dataclass
class FakeUser:
    id: int = 10001
    username: str = "fake_user"
    first_name: str = "Fake"
    last_name: str = "Account"
    phone: str = "10000000000"


class FakeSession:
    def __init__(self, value="fake-session-result"):
        self.value = value

    def save(self):
        return self.value


class FakeTelegramClient:
    def __init__(
        self,
        *,
        authorized=True,
        send_error=None,
        code_error=None,
        password_error=None,
        auth_error=None,
        me_error=None,
        connect_delay=0,
    ):
        self.session = FakeSession()
        self.authorized = authorized
        self.send_error = send_error
        self.code_error = code_error
        self.password_error = password_error
        self.auth_error = auth_error
        self.me_error = me_error
        self.connect_delay = connect_delay
        self.connected = False
        self.disconnected = False
        self.calls = []

    async def connect(self):
        self.calls.append(("connect",))
        if self.connect_delay:
            await asyncio.sleep(self.connect_delay)
        self.connected = True

    async def disconnect(self):
        self.calls.append(("disconnect",))
        self.disconnected = True

    async def send_code_request(self, phone):
        self.calls.append(("send_code_request", phone))
        if self.send_error:
            raise self.send_error
        return type("SentCode", (), {"phone_code_hash": "fake-phone-code-hash"})()

    async def sign_in(self, **kwargs):
        safe_kwargs = {key: value for key, value in kwargs.items() if key not in {"code", "password"}}
        self.calls.append(("sign_in", safe_kwargs))
        error = self.password_error if "password" in kwargs else self.code_error
        if error:
            raise error
        return FakeUser()

    async def is_user_authorized(self):
        self.calls.append(("is_user_authorized",))
        if self.auth_error:
            raise self.auth_error
        return self.authorized

    async def get_me(self):
        self.calls.append(("get_me",))
        if self.me_error:
            raise self.me_error
        return FakeUser()


@override_settings(SECRET_KEY="fake-test-secret", CONFIG_ENCRYPTION_KEY="fake-config-key")
class TelegramAccountServiceTests(TestCase):
    def setUp(self):
        super().setUp()
        self.env = patch.dict(
            os.environ,
            {
                "ENABLE_TELEGRAM_ACCOUNT_NETWORK": "1",
                "TELEGRAM_API_ID": "",
                "TELEGRAM_API_HASH": "",
            },
            clear=False,
        )
        self.env.start()
        self.addCleanup(self.env.stop)
        BotSettings.objects.create(
            telegram_api_id="123456",
            telegram_api_hash="fake-api-hash",
        )

    def factory_for(self, client):
        return patch(
            "botcore.services.telegram_accounts.create_telegram_client",
            return_value=client,
        )

    def assert_safe_error(self, error, *sensitive_values):
        self.assertIsNone(error.__context__)
        self.assertIsNone(error.__cause__)
        rendered = f"{error!s} {error!r} {''.join(traceback.format_exception(error))}"
        for value in sensitive_values:
            self.assertNotIn(value, rendered)

    def test_normalize_phone_accepts_international_variants(self):
        self.assertEqual(normalize_phone("００ (８６) 138-0000.0000"), "+8613800000000")
        self.assertEqual(normalize_phone("+1 (202) 555-0100"), "+12025550100")

    def test_normalize_phone_rejects_missing_country_code_and_bad_length(self):
        for value in [
            "13800000000",
            "+012345678",
            "+1234567",
            "+1234567890123456",
        ]:
            with self.subTest(value=value), self.assertRaises(TelegramAccountError) as caught:
                normalize_phone(value)
            self.assertEqual(caught.exception.code, "invalid_phone")

    def test_normalize_phone_rejects_unicode_digits(self):
        with self.assertRaises(TelegramAccountError) as caught:
            normalize_phone("+12٢55550100")

        self.assertEqual(caught.exception.code, "invalid_phone")

    def test_client_factory_disables_updates_and_automatic_flood_wait(self):
        fake_session = object()
        fake_client = object()
        with patch(
            "botcore.services.telegram_accounts.StringSession",
            return_value=fake_session,
        ) as string_session, patch(
            "botcore.services.telegram_accounts.TelegramClient",
            return_value=fake_client,
        ) as telegram_client:
            result = create_telegram_client("fake-input-session", 123456, "fake-api-hash")

        self.assertIs(result, fake_client)
        string_session.assert_called_once_with("fake-input-session")
        self.assertEqual(telegram_client.call_args.args, (fake_session, 123456, "fake-api-hash"))
        self.assertFalse(telegram_client.call_args.kwargs["receive_updates"])
        self.assertEqual(telegram_client.call_args.kwargs["flood_sleep_threshold"], 0)

    def test_network_is_disabled_by_default_before_client_creation(self):
        with patch.dict(os.environ, {"ENABLE_TELEGRAM_ACCOUNT_NETWORK": ""}, clear=False), patch(
            "botcore.services.telegram_accounts.create_telegram_client"
        ) as factory, self.assertRaises(TelegramAccountError) as caught:
            send_login_code("+12025550100")

        self.assertEqual(caught.exception.code, "network_disabled")
        factory.assert_not_called()

    def test_credentials_reject_missing_and_invalid_api_id(self):
        settings = BotSettings.load()
        settings.telegram_api_id = ""
        settings.telegram_api_hash = ""
        settings.save()
        with self.assertRaises(TelegramAccountError) as missing:
            send_login_code("+12025550100")
        self.assertEqual(missing.exception.code, "credentials_missing")

        settings.telegram_api_id = "not-a-number"
        settings.telegram_api_hash = "fake-api-hash"
        settings.save()
        with self.assertRaises(TelegramAccountError) as invalid:
            send_login_code("+12025550100")
        self.assertEqual(invalid.exception.code, "invalid_api_id")

    def test_credentials_fall_back_to_environment(self):
        settings = BotSettings.load()
        settings.telegram_api_id = ""
        settings.telegram_api_hash = ""
        settings.save()
        client = FakeTelegramClient()

        with patch.dict(
            os.environ,
            {"TELEGRAM_API_ID": "654321", "TELEGRAM_API_HASH": "fake-env-api-hash"},
            clear=False,
        ), self.factory_for(client) as factory:
            send_login_code("+12025550100")

        _, api_id, api_hash = factory.call_args.args
        self.assertEqual(api_id, 654321)
        self.assertEqual(api_hash, "fake-env-api-hash")

    def test_database_credentials_take_precedence_over_environment(self):
        client = FakeTelegramClient()
        with patch.dict(
            os.environ,
            {"TELEGRAM_API_ID": "654321", "TELEGRAM_API_HASH": "fake-env-api-hash"},
            clear=False,
        ), self.factory_for(client) as factory:
            send_login_code("+12025550100")

        _, api_id, api_hash = factory.call_args.args
        self.assertEqual(api_id, 123456)
        self.assertEqual(api_hash, "fake-api-hash")

    def test_send_login_code_returns_hash_and_session_and_disconnects(self):
        client = FakeTelegramClient()
        with self.factory_for(client):
            result = send_login_code("+1 (202) 555-0100")

        self.assertEqual(result.phone, "+12025550100")
        self.assertEqual(result.phone_code_hash, "fake-phone-code-hash")
        self.assertEqual(result.session_string, "fake-session-result")
        self.assertNotIn("fake-session-result", repr(result))
        self.assertNotIn("fake-phone-code-hash", repr(result))
        self.assertTrue(client.disconnected)

    def test_code_login_without_password_returns_user(self):
        client = FakeTelegramClient()
        with self.factory_for(client) as factory:
            result = sign_in_with_code(
                "+12025550100",
                "00000",
                "fake-phone-code-hash",
                "fake-input-session",
            )

        self.assertFalse(result.requires_password)
        self.assertEqual(result.session_string, "fake-session-result")
        self.assertEqual(result.user.telegram_id, 10001)
        self.assertNotIn("fake-input-session", repr(result))
        self.assertEqual(factory.call_args.args[0], "fake-input-session")
        self.assertTrue(client.disconnected)

    def test_code_login_reports_password_requirement(self):
        client = FakeTelegramClient(code_error=errors.SessionPasswordNeededError(None))
        with self.factory_for(client):
            result = sign_in_with_code(
                "+12025550100",
                "00000",
                "fake-phone-code-hash",
                "fake-input-session",
            )

        self.assertTrue(result.requires_password)
        self.assertIsNone(result.user)
        self.assertEqual(result.session_string, "fake-session-result")
        self.assertTrue(client.disconnected)

    def test_password_login_returns_authorized_user(self):
        client = FakeTelegramClient()
        with self.factory_for(client) as factory:
            result = sign_in_with_password("fake-password", "fake-input-session")

        self.assertFalse(result.requires_password)
        self.assertEqual(result.user.username, "fake_user")
        self.assertEqual(factory.call_args.args[0], "fake-input-session")
        self.assertTrue(client.disconnected)

    def test_session_check_returns_authorized_or_unauthorized(self):
        authorized = FakeTelegramClient(authorized=True)
        with self.factory_for(authorized) as factory:
            result = check_session("fake-authorized-session")
        self.assertTrue(result.authorized)
        self.assertEqual(result.user.telegram_id, 10001)
        self.assertEqual(factory.call_args.args[0], "fake-authorized-session")
        self.assertTrue(authorized.disconnected)

        unauthorized = FakeTelegramClient(authorized=False)
        with self.factory_for(unauthorized):
            result = check_session("fake-unauthorized-session")
        self.assertFalse(result.authorized)
        self.assertIsNone(result.user)
        self.assertTrue(unauthorized.disconnected)

    def test_timeout_is_converted_and_disconnects(self):
        client = FakeTelegramClient(connect_delay=0.05)
        with patch("botcore.services.telegram_accounts.OPERATION_TIMEOUT_SECONDS", 0.001), self.factory_for(
            client
        ), self.assertRaises(TelegramAccountError) as caught:
            send_login_code("+12025550100")

        self.assertEqual(caught.exception.code, "timeout")
        self.assertTrue(client.disconnected)

    def test_code_errors_are_converted_safely(self):
        cases = [
            (errors.PhoneCodeInvalidError(None), "invalid_code"),
            (errors.PhoneCodeExpiredError(None), "expired_code"),
        ]
        for source_error, expected_code in cases:
            client = FakeTelegramClient(code_error=source_error)
            with self.subTest(expected_code=expected_code), self.factory_for(client), self.assertRaises(
                TelegramAccountError
            ) as caught:
                sign_in_with_code(
                    "+12025550100",
                    "fake-secret-code",
                    "fake-phone-code-hash",
                    "fake-input-session",
                )
            self.assertEqual(caught.exception.code, expected_code)
            self.assert_safe_error(
                caught.exception,
                "fake-secret-code",
                "fake-phone-code-hash",
                "fake-input-session",
            )
            self.assertTrue(client.disconnected)

    def test_invalid_password_is_converted_safely(self):
        client = FakeTelegramClient(password_error=errors.PasswordHashInvalidError(None))
        with self.factory_for(client), self.assertRaises(TelegramAccountError) as caught:
            sign_in_with_password("fake-secret-password", "fake-input-session")

        self.assertEqual(caught.exception.code, "invalid_password")
        self.assert_safe_error(caught.exception, "fake-secret-password", "fake-input-session")
        self.assertTrue(client.disconnected)

    def test_flood_wait_exposes_only_retry_after(self):
        client = FakeTelegramClient(send_error=errors.FloodWaitError(None, capture=37))
        with self.factory_for(client), self.assertRaises(TelegramAccountError) as caught:
            send_login_code("+12025550100")

        self.assertEqual(caught.exception.code, "flood_wait")
        self.assertEqual(caught.exception.retry_after, 37)
        self.assertTrue(client.disconnected)

    def test_common_network_error_is_converted_and_disconnects(self):
        client = FakeTelegramClient(send_error=ConnectionError("fake-sensitive-network-detail"))
        with self.factory_for(client), self.assertRaises(TelegramAccountError) as caught:
            send_login_code("+12025550100")

        self.assertEqual(caught.exception.code, "network_error")
        self.assert_safe_error(caught.exception, "fake-sensitive-network-detail")
        self.assertTrue(client.disconnected)

    def test_session_authorization_error_is_converted_and_disconnects(self):
        client = FakeTelegramClient(
            auth_error=ConnectionError("fake-sensitive-authorization-detail")
        )
        with self.factory_for(client), self.assertRaises(TelegramAccountError) as caught:
            check_session("fake-input-session")

        self.assertEqual(caught.exception.code, "network_error")
        self.assert_safe_error(caught.exception, "fake-sensitive-authorization-detail")
        self.assertTrue(client.disconnected)

    def test_session_get_me_error_is_converted_and_disconnects(self):
        client = FakeTelegramClient(
            me_error=OSError("fake-sensitive-get-me-detail")
        )
        with self.factory_for(client), self.assertRaises(TelegramAccountError) as caught:
            check_session("fake-input-session")

        self.assertEqual(caught.exception.code, "network_error")
        self.assert_safe_error(caught.exception, "fake-sensitive-get-me-detail")
        self.assertTrue(client.disconnected)

    def test_unauthorized_subclasses_map_to_expired_session_and_disconnect(self):
        unauthorized_errors = [
            errors.AuthKeyPermEmptyError(None),
            errors.UserDeactivatedBanError(None),
        ]
        for source_error in unauthorized_errors:
            client = FakeTelegramClient(auth_error=source_error)
            with self.subTest(error_type=type(source_error).__name__), self.factory_for(
                client
            ), self.assertRaises(TelegramAccountError) as caught:
                check_session("fake-input-session")

            self.assertEqual(caught.exception.code, "session_unauthorized")
            self.assertIn("会话已失效", caught.exception.message)
            self.assert_safe_error(caught.exception, "fake-input-session")
            self.assertTrue(client.disconnected)
