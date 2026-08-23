import asyncio
import json
import os
import traceback
from dataclasses import dataclass
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.db import IntegrityError, OperationalError, connection, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from telethon import errors
from rest_framework.test import APIClient

from botcore.crypto import decrypt_text, encrypt_text
from botcore.models import BotSettings, TelegramBot, TelegramLoginAccount
from botcore.services import telegram_accounts as telegram_account_service_module
from botcore.services.telegram_accounts import (
    CodeSentResult,
    LoginResult,
    SessionCheckResult,
    TelegramAccountError,
    TelegramUserInfo,
    check_session,
    create_telegram_client,
    normalize_phone,
    send_login_code,
    sign_in_with_code,
    sign_in_with_password,
    validate_runtime_configuration,
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

    def test_phone_is_database_unique(self):
        TelegramLoginAccount.objects.create(
            label="First fake account",
            phone="+12025550100",
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            TelegramLoginAccount.objects.create(
                label="Duplicate fake account",
                phone="+12025550100",
            )

    def test_phone_cannot_be_empty(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            TelegramLoginAccount.objects.create(
                label="Missing phone account",
                phone="",
            )

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

    def test_runtime_configuration_validation_has_no_client_or_secret_result(self):
        with patch(
            "botcore.services.telegram_accounts.create_telegram_client",
        ) as create_client:
            result = telegram_account_service_module.validate_runtime_configuration()

        self.assertIsNone(result)
        create_client.assert_not_called()

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


@override_settings(SECRET_KEY="fake-test-secret", CONFIG_ENCRYPTION_KEY="fake-config-key")
class TelegramAccountApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.runtime_preflight = patch(
            "botcore.views.telegram_account_service.validate_runtime_configuration",
        )
        self.runtime_preflight.start()
        self.addCleanup(self.runtime_preflight.stop)

    def create_account(self, **overrides):
        values = {
            "label": "Fake account",
            "phone": "+12025550100",
            "status": TelegramLoginAccount.Status.PENDING,
        }
        values.update(overrides)
        return TelegramLoginAccount.objects.create(**values)

    def assert_response_has_no_secrets(self, value):
        forbidden_keys = {
            "telegram_api_hash", "api_hash", "phone_code_hash",
            "session", "session_string", "code", "password",
        }
        if isinstance(value, dict):
            for key, nested in value.items():
                self.assertNotIn(str(key).lower(), forbidden_keys)
                self.assert_response_has_no_secrets(nested)
        elif isinstance(value, (list, tuple)):
            for nested in value:
                self.assert_response_has_no_secrets(nested)
        rendered = json.dumps(value, ensure_ascii=False, default=str)
        for secret in {
            "fake-api-hash",
            "fake-final-session",
            "fake-new-phone-code-hash",
            "fake-new-session",
            "fake-password-session",
            "fake-phone-code-hash",
            "fake-secret-code",
            "fake-secret-password",
            "fake-session-string",
            "fake-stale-session",
            "fake-telegram-api-hash",
        }:
            self.assertNotIn(secret, rendered)

    def test_list_retrieve_and_delete_expose_only_public_account_fields(self):
        account = self.create_account(
            telegram_id=10001,
            username="fake_user",
            first_name="Fake",
            last_name="Account",
            status=TelegramLoginAccount.Status.LOGGED_IN,
            phone_code_hash="fake-phone-code-hash",
            session_string="fake-session-string",
            last_error="safe summary\n" + ("x" * 600),
            last_checked_at=timezone.now(),
        )
        self.create_account(phone="+12025550101", label="Second account")

        listed = self.client.get("/api/telegram-accounts/", {"page_size": 1})
        retrieved = self.client.get(f"/api/telegram-accounts/{account.pk}/")

        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.data["count"], 2)
        self.assertEqual(len(listed.data["results"]), 1)
        self.assertEqual(retrieved.status_code, 200)
        self.assertEqual(retrieved.data["telegram_id"], 10001)
        self.assertTrue(retrieved.data["has_session"])
        self.assertLessEqual(len(retrieved.data["last_error"]), 500)
        self.assertNotIn("\n", retrieved.data["last_error"])
        self.assert_response_has_no_secrets(listed.data)
        self.assert_response_has_no_secrets(retrieved.data)

        generic_create = self.client.post(
            "/api/telegram-accounts/",
            {"label": "Blocked", "phone": "+12025550102"},
            format="json",
        )
        generic_update = self.client.patch(
            f"/api/telegram-accounts/{account.pk}/",
            {"label": "Blocked"},
            format="json",
        )

        self.assertEqual(generic_create.status_code, 405)
        self.assertEqual(generic_update.status_code, 405)

        with patch("botcore.views.telegram_account_service") as service:
            deleted = self.client.delete(f"/api/telegram-accounts/{account.pk}/")

        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(TelegramLoginAccount.objects.filter(pk=account.pk).exists())
        service.send_login_code.assert_not_called()
        service.sign_in_with_code.assert_not_called()
        service.sign_in_with_password.assert_not_called()
        service.check_session.assert_not_called()

    def test_start_creates_and_reuses_account_without_exposing_secrets(self):
        result = CodeSentResult(
            phone="+12025550100",
            phone_code_hash="fake-phone-code-hash",
            session_string="fake-session-string",
        )
        with patch("botcore.views.telegram_account_service.send_login_code", return_value=result) as send:
            created = self.client.post("/api/telegram-accounts/login/start/", {
                "phone": "+1 (202) 555-0100",
                "label": "Primary",
            }, format="json")
            reused = self.client.post("/api/telegram-accounts/login/start/", {
                "phone": "+12025550100",
                "label": "Renamed",
            }, format="json")

        self.assertEqual(created.status_code, 200)
        self.assertEqual(reused.status_code, 200)
        self.assertEqual(created.data["account_id"], reused.data["account_id"])
        self.assertEqual(created.data["next_step"], "code")
        self.assertEqual(TelegramLoginAccount.objects.count(), 1)
        account = TelegramLoginAccount.objects.get()
        self.assertEqual(account.label, "Renamed")
        self.assertEqual(account.status, TelegramLoginAccount.Status.CODE_SENT)
        self.assertEqual(account.phone_code_hash_plain, "fake-phone-code-hash")
        self.assertEqual(account.session_string_plain, "fake-session-string")
        self.assertEqual(send.call_count, 2)
        self.assert_response_has_no_secrets(created.data)
        self.assert_response_has_no_secrets(reused.data)

    def test_start_preflight_failure_does_not_create_or_mutate_accounts(self):
        logged_in = self.create_account(
            status=TelegramLoginAccount.Status.LOGGED_IN,
            session_string="fake-session-string",
        )
        code_sent = self.create_account(
            phone="+12025550101",
            status=TelegramLoginAccount.Status.CODE_SENT,
            phone_code_hash="fake-phone-code-hash",
            session_string="fake-new-session",
        )
        snapshots = {
            account.pk: self._account_state(account)
            for account in (logged_in, code_sent)
        }
        with patch.dict(
            os.environ,
            {"ENABLE_TELEGRAM_ACCOUNT_NETWORK": "0"},
            clear=False,
        ), patch(
            "botcore.views.telegram_account_service.validate_runtime_configuration",
            wraps=validate_runtime_configuration,
        ), patch(
            "botcore.views.telegram_account_service.send_login_code",
        ) as send:
            responses = [
                self.client.post("/api/telegram-accounts/login/start/", {
                    "phone": logged_in.phone,
                }, format="json"),
                self.client.post("/api/telegram-accounts/login/start/", {
                    "phone": code_sent.phone,
                }, format="json"),
                self.client.post("/api/telegram-accounts/login/start/", {
                    "phone": "+12025550102",
                }, format="json"),
            ]

        self.assertTrue(all(response.status_code == 503 for response in responses))
        self.assertEqual(TelegramLoginAccount.objects.count(), 2)
        send.assert_not_called()
        for account in (logged_in, code_sent):
            account.refresh_from_db()
            self.assertEqual(self._account_state(account), snapshots[account.pk])

    def test_start_credentials_preflight_failure_keeps_database_empty(self):
        with patch.dict(
            os.environ,
            {
                "ENABLE_TELEGRAM_ACCOUNT_NETWORK": "1",
                "TELEGRAM_API_ID": "",
                "TELEGRAM_API_HASH": "",
            },
            clear=False,
        ), patch(
            "botcore.views.telegram_account_service.validate_runtime_configuration",
            wraps=validate_runtime_configuration,
        ), patch(
            "botcore.views.telegram_account_service.send_login_code",
        ) as send:
            response = self.client.post("/api/telegram-accounts/login/start/", {
                "phone": "+12025550100",
            }, format="json")

        self.assertEqual(response.status_code, 503)
        self.assertFalse(TelegramLoginAccount.objects.exists())
        send.assert_not_called()

    def test_start_integrity_race_returns_winner_without_external_call(self):
        race_winner = TelegramLoginAccount(
            id=99,
            label="Race winner",
            phone="+12025550100",
            status=TelegramLoginAccount.Status.PENDING,
            login_attempt_id="winner-attempt",
            login_attempt_started_at=timezone.now(),
        )
        locked_queryset = MagicMock()
        locked_queryset.filter.return_value.first.return_value = None
        locked_queryset.get.return_value = race_winner
        result = CodeSentResult(
            phone="+12025550100",
            phone_code_hash="fake-phone-code-hash",
            session_string="fake-session-string",
        )
        with patch(
            "botcore.views.telegram_account_service.send_login_code",
            return_value=result,
        ) as send, patch(
            "botcore.views.TelegramLoginAccount.objects.select_for_update",
            return_value=locked_queryset,
        ), patch(
            "botcore.views.TelegramLoginAccount.objects.create",
            side_effect=IntegrityError,
        ):
            response = self.client.post("/api/telegram-accounts/login/start/", {
                "phone": "+12025550100",
            }, format="json")

        self.assertEqual(response.status_code, 409)
        send.assert_not_called()
        locked_queryset.get.assert_called_once_with(phone="+12025550100")
        self.assert_response_has_no_secrets(response.data)

    def test_start_lock_wait_observes_fresh_attempt_and_does_not_resend(self):
        account = self.create_account(status=TelegramLoginAccount.Status.PENDING)
        locked_queryset = MagicMock()

        def locked_first():
            refreshed = TelegramLoginAccount.objects.get(pk=account.pk)
            refreshed.login_attempt_id = "winner-attempt"
            refreshed.login_attempt_started_at = timezone.now()
            refreshed.save()
            return refreshed

        locked_queryset.filter.return_value.first.side_effect = locked_first
        with patch(
            "botcore.views.TelegramLoginAccount.objects.select_for_update",
            return_value=locked_queryset,
        ), patch(
            "botcore.views.telegram_account_service.send_login_code",
        ) as send:
            response = self.client.post("/api/telegram-accounts/login/start/", {
                "phone": account.phone,
            }, format="json")

        self.assertEqual(response.status_code, 409)
        send.assert_not_called()
        self.assert_response_has_no_secrets(response.data)

    def test_start_database_lock_error_is_safe_and_does_not_call_service(self):
        result = CodeSentResult(
            phone="+12025550100",
            phone_code_hash="fake-phone-code-hash",
            session_string="fake-session-string",
        )
        with patch(
            "botcore.views.TelegramLoginAccount.objects.create",
            side_effect=OperationalError("database is locked"),
        ), patch(
            "botcore.views.telegram_account_service.send_login_code",
            return_value=result,
        ) as send:
            response = self.client.post("/api/telegram-accounts/login/start/", {
                "phone": "+12025550100",
            }, format="json")

        self.assertEqual(response.status_code, 409)
        send.assert_not_called()
        self.assertNotIn("database is locked", str(response.data))
        self.assert_response_has_no_secrets(response.data)

    def test_start_non_lock_database_error_is_not_disguised_as_conflict(self):
        with patch(
            "botcore.views.TelegramLoginAccount.objects.create",
            side_effect=OperationalError("disk I/O error"),
        ), self.assertRaises(OperationalError):
            self.client.post("/api/telegram-accounts/login/start/", {
                "phone": "+12025550100",
            }, format="json")

    def test_code_login_completes_public_identity(self):
        account = self.create_account(
            status=TelegramLoginAccount.Status.CODE_SENT,
            phone_code_hash="fake-phone-code-hash",
            session_string="fake-session-string",
        )
        result = LoginResult(
            requires_password=False,
            session_string="fake-final-session",
            user=TelegramUserInfo(10001, "fake_user", "Fake", "Account"),
        )
        with patch("botcore.views.telegram_account_service.sign_in_with_code", return_value=result) as sign_in:
            response = self.client.post("/api/telegram-accounts/login/code/", {
                "account_id": account.pk,
                "code": "00000",
            }, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["next_step"], "complete")
        account.refresh_from_db()
        self.assertEqual(account.status, TelegramLoginAccount.Status.LOGGED_IN)
        self.assertEqual(account.telegram_id, 10001)
        self.assertEqual(account.phone_code_hash, "")
        self.assertEqual(account.session_string_plain, "fake-final-session")
        self.assertIsNotNone(account.last_checked_at)
        sign_in.assert_called_once_with(
            account.phone, "00000", "fake-phone-code-hash", "fake-session-string",
        )
        self.assert_response_has_no_secrets(response.data)

    def test_code_login_can_require_password_then_password_completes(self):
        account = self.create_account(
            status=TelegramLoginAccount.Status.CODE_SENT,
            phone_code_hash="fake-phone-code-hash",
            session_string="fake-session-string",
        )
        password_required = LoginResult(
            requires_password=True,
            session_string="fake-password-session",
        )
        completed = LoginResult(
            requires_password=False,
            session_string="fake-final-session",
            user=TelegramUserInfo(10001, "fake_user", "Fake", "Account"),
        )
        with patch(
            "botcore.views.telegram_account_service.sign_in_with_code",
            return_value=password_required,
        ):
            code_response = self.client.post("/api/telegram-accounts/login/code/", {
                "account_id": account.pk,
                "code": "00000",
            }, format="json")

        self.assertEqual(code_response.status_code, 200)
        self.assertEqual(code_response.data["next_step"], "password")
        account.refresh_from_db()
        self.assertEqual(account.status, TelegramLoginAccount.Status.PASSWORD_REQUIRED)
        self.assertEqual(account.session_string_plain, "fake-password-session")

        with patch(
            "botcore.views.telegram_account_service.sign_in_with_password",
            return_value=completed,
        ) as sign_in:
            password_response = self.client.post("/api/telegram-accounts/login/password/", {
                "account_id": account.pk,
                "password": "fake-secret-password",
            }, format="json")

        self.assertEqual(password_response.status_code, 200)
        self.assertEqual(password_response.data["next_step"], "complete")
        account.refresh_from_db()
        self.assertEqual(account.status, TelegramLoginAccount.Status.LOGGED_IN)
        self.assertEqual(account.telegram_id, 10001)
        sign_in.assert_called_once_with("fake-secret-password", "fake-password-session")
        self.assert_response_has_no_secrets(code_response.data)
        self.assert_response_has_no_secrets(password_response.data)

    def test_check_refreshes_authorized_account_or_marks_session_expired(self):
        account = self.create_account(
            status=TelegramLoginAccount.Status.LOGGED_IN,
            session_string="fake-session-string",
        )
        authorized = SessionCheckResult(
            authorized=True,
            user=TelegramUserInfo(10001, "refreshed", "New", "Name"),
        )
        with patch("botcore.views.telegram_account_service.check_session", return_value=authorized):
            response = self.client.post(f"/api/telegram-accounts/{account.pk}/check/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], TelegramLoginAccount.Status.LOGGED_IN)
        self.assertEqual(response.data["username"], "refreshed")
        self.assert_response_has_no_secrets(response.data)

        with patch(
            "botcore.views.telegram_account_service.check_session",
            return_value=SessionCheckResult(authorized=False),
        ):
            response = self.client.post(f"/api/telegram-accounts/{account.pk}/check/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], TelegramLoginAccount.Status.SESSION_EXPIRED)
        self.assert_response_has_no_secrets(response.data)

    def test_check_unauthorized_service_error_marks_expired_and_returns_account(self):
        account = self.create_account(
            status=TelegramLoginAccount.Status.LOGGED_IN,
            session_string="fake-session-string",
        )
        error = TelegramAccountError(
            "Telegram 会话已失效，请重新登录。",
            code="session_unauthorized",
        )

        with patch(
            "botcore.views.telegram_account_service.check_session",
            side_effect=error,
        ):
            response = self.client.post(f"/api/telegram-accounts/{account.pk}/check/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], account.pk)
        self.assertEqual(response.data["status"], TelegramLoginAccount.Status.SESSION_EXPIRED)
        self.assertIn("会话已失效", response.data["last_error"])
        self.assert_response_has_no_secrets(response.data)

    def test_login_actions_validate_input_state_and_session_before_service_calls(self):
        pending = self.create_account()
        code_sent = self.create_account(
            phone="+12025550101",
            status=TelegramLoginAccount.Status.CODE_SENT,
        )
        password_required = self.create_account(
            phone="+12025550102",
            status=TelegramLoginAccount.Status.PASSWORD_REQUIRED,
        )
        with patch("botcore.views.telegram_account_service") as service:
            responses = [
                self.client.post("/api/telegram-accounts/login/start/", {"phone": "invalid"}, format="json"),
                self.client.post("/api/telegram-accounts/login/code/", {"account_id": pending.pk, "code": "1"}, format="json"),
                self.client.post("/api/telegram-accounts/login/code/", {"account_id": code_sent.pk, "code": ""}, format="json"),
                self.client.post("/api/telegram-accounts/login/password/", {"account_id": code_sent.pk, "password": "x"}, format="json"),
                self.client.post("/api/telegram-accounts/login/password/", {"account_id": password_required.pk, "password": ""}, format="json"),
                self.client.post(f"/api/telegram-accounts/{pending.pk}/check/"),
            ]

        self.assertTrue(all(response.status_code == 400 for response in responses))
        for response in responses:
            self.assert_response_has_no_secrets(response.data)
        service.send_login_code.assert_not_called()
        service.sign_in_with_code.assert_not_called()
        service.sign_in_with_password.assert_not_called()
        service.check_session.assert_not_called()

    def test_service_errors_are_safe_and_use_stable_http_statuses(self):
        account = self.create_account(
            status=TelegramLoginAccount.Status.CODE_SENT,
            phone_code_hash="fake-phone-code-hash",
            session_string="fake-session-string",
        )
        cases = [
            (TelegramAccountError("Telegram 账号网络访问未启用。", code="network_disabled"), 503),
            (TelegramAccountError("Telegram API 凭据未配置完整。", code="credentials_missing"), 503),
            (TelegramAccountError("操作过于频繁，请稍后重试。", code="flood_wait", retry_after=12), 429),
            (TelegramAccountError("无法连接 Telegram，请稍后重试。", code="network_error"), 502),
            (TelegramAccountError("验证码错误，请重新输入。", code="invalid_code"), 400),
        ]
        for error, expected_status in cases:
            with self.subTest(error=error.code), patch(
                "botcore.views.telegram_account_service.sign_in_with_code",
                side_effect=error,
            ):
                response = self.client.post("/api/telegram-accounts/login/code/", {
                    "account_id": account.pk,
                    "code": "fake-secret-code",
                }, format="json")

            self.assertEqual(response.status_code, expected_status)
            self.assert_response_has_no_secrets(response.data)
            self.assertNotIn("fake-secret-code", str(response.data))
            account.refresh_from_db()
            self.assertLessEqual(len(account.last_error), 500)

    def test_late_code_error_cannot_overwrite_new_login_attempt(self):
        account = self.create_account(
            status=TelegramLoginAccount.Status.CODE_SENT,
            phone_code_hash="fake-old-phone-code-hash",
            session_string="fake-old-session",
        )

        def late_error(*args):
            refreshed = TelegramLoginAccount.objects.get(pk=account.pk)
            refreshed.phone_code_hash = "fake-new-phone-code-hash"
            refreshed.session_string = "fake-new-session"
            refreshed.last_error = ""
            refreshed.save()
            raise TelegramAccountError("旧验证码错误。", code="invalid_code")

        with patch(
            "botcore.views.telegram_account_service.sign_in_with_code",
            side_effect=late_error,
        ):
            response = self.client.post("/api/telegram-accounts/login/code/", {
                "account_id": account.pk,
                "code": "00000",
            }, format="json")

        self.assertEqual(response.status_code, 409)
        account.refresh_from_db()
        self.assertEqual(account.phone_code_hash_plain, "fake-new-phone-code-hash")
        self.assertEqual(account.session_string_plain, "fake-new-session")
        self.assertEqual(account.last_error, "")

    def test_late_check_error_cannot_overwrite_newer_success(self):
        account = self.create_account(
            status=TelegramLoginAccount.Status.LOGGED_IN,
            session_string="fake-session-string",
            username="old_name",
        )

        def late_error(*args):
            refreshed = TelegramLoginAccount.objects.get(pk=account.pk)
            refreshed.username = "new_name"
            refreshed.last_checked_at = timezone.now()
            refreshed.last_error = ""
            refreshed.save()
            raise TelegramAccountError("迟到的网络错误。", code="network_error")

        with patch(
            "botcore.views.telegram_account_service.check_session",
            side_effect=late_error,
        ):
            response = self.client.post(f"/api/telegram-accounts/{account.pk}/check/")

        self.assertEqual(response.status_code, 409)
        account.refresh_from_db()
        self.assertEqual(account.username, "new_name")
        self.assertEqual(account.last_error, "")

    def test_error_write_does_not_block_earlier_successful_code_result(self):
        account = self.create_account(
            status=TelegramLoginAccount.Status.CODE_SENT,
            phone_code_hash="fake-phone-code-hash",
            session_string="fake-session-string",
        )
        successful_result = LoginResult(
            requires_password=False,
            session_string="fake-final-session",
            user=TelegramUserInfo(10001, "fake_user", "Fake", "Account"),
        )
        call_count = 0

        def overlapping_sign_in(*args):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise TelegramAccountError("验证码错误，请重新输入。", code="invalid_code")
            inner_response = self.client.post("/api/telegram-accounts/login/code/", {
                "account_id": account.pk,
                "code": "11111",
            }, format="json")
            self.assertEqual(inner_response.status_code, 400)
            return successful_result

        with patch(
            "botcore.views.telegram_account_service.sign_in_with_code",
            side_effect=overlapping_sign_in,
        ):
            response = self.client.post("/api/telegram-accounts/login/code/", {
                "account_id": account.pk,
                "code": "00000",
            }, format="json")

        self.assertEqual(response.status_code, 200)
        account.refresh_from_db()
        self.assertEqual(account.status, TelegramLoginAccount.Status.LOGGED_IN)
        self.assertEqual(account.session_string_plain, "fake-final-session")
        self.assertEqual(account.last_error, "")
        self.assert_response_has_no_secrets(response.data)

    def test_start_password_and_check_service_errors_preserve_safe_states(self):
        network_disabled = TelegramAccountError(
            "Telegram 账号网络访问未启用。",
            code="network_disabled",
        )
        with patch(
            "botcore.views.telegram_account_service.send_login_code",
            side_effect=network_disabled,
        ):
            start_response = self.client.post("/api/telegram-accounts/login/start/", {
                "phone": "+12025550100",
            }, format="json")

        self.assertEqual(start_response.status_code, 503)
        failed_account = TelegramLoginAccount.objects.get()
        self.assertEqual(failed_account.status, TelegramLoginAccount.Status.ERROR)
        self.assertEqual(failed_account.login_attempt_id, "")
        self.assertIsNone(failed_account.login_attempt_started_at)
        self.assert_response_has_no_secrets(start_response.data)

        account = self.create_account(
            phone="+12025550101",
            status=TelegramLoginAccount.Status.PASSWORD_REQUIRED,
            session_string="fake-password-session",
        )
        invalid_password = TelegramAccountError(
            "二级密码错误，请重新输入。",
            code="invalid_password",
        )
        with patch(
            "botcore.views.telegram_account_service.sign_in_with_password",
            side_effect=invalid_password,
        ):
            password_response = self.client.post("/api/telegram-accounts/login/password/", {
                "account_id": account.pk,
                "password": "fake-secret-password",
            }, format="json")

        self.assertEqual(password_response.status_code, 400)
        account.refresh_from_db()
        self.assertEqual(account.status, TelegramLoginAccount.Status.PASSWORD_REQUIRED)
        self.assertIn("密码错误", account.last_error)
        self.assert_response_has_no_secrets(password_response.data)
        self.assertNotIn("fake-secret-password", str(password_response.data))

        network_error = TelegramAccountError(
            "无法连接 Telegram，请稍后重试。",
            code="network_error",
        )
        with patch(
            "botcore.views.telegram_account_service.check_session",
            side_effect=network_error,
        ):
            check_response = self.client.post(f"/api/telegram-accounts/{account.pk}/check/")

        self.assertEqual(check_response.status_code, 502)
        account.refresh_from_db()
        self.assertEqual(account.status, TelegramLoginAccount.Status.PASSWORD_REQUIRED)
        self.assertIn("无法连接", account.last_error)
        self.assert_response_has_no_secrets(check_response.data)

    def test_stale_code_request_cannot_overwrite_newer_state(self):
        account = self.create_account(
            status=TelegramLoginAccount.Status.CODE_SENT,
            phone_code_hash="fake-phone-code-hash",
            session_string="fake-session-string",
        )

        def stale_result(*args):
            TelegramLoginAccount.objects.filter(pk=account.pk).update(
                status=TelegramLoginAccount.Status.PASSWORD_REQUIRED,
            )
            return LoginResult(
                requires_password=False,
                session_string="fake-stale-session",
                user=TelegramUserInfo(10001),
            )

        with patch(
            "botcore.views.telegram_account_service.sign_in_with_code",
            side_effect=stale_result,
        ):
            response = self.client.post("/api/telegram-accounts/login/code/", {
                "account_id": account.pk,
                "code": "00000",
            }, format="json")

        self.assertEqual(response.status_code, 409)
        account.refresh_from_db()
        self.assertEqual(account.status, TelegramLoginAccount.Status.PASSWORD_REQUIRED)
        self.assertNotEqual(account.session_string_plain, "fake-stale-session")

    def test_stale_code_request_cannot_overwrite_newer_code_sent_session(self):
        account = self.create_account(
            status=TelegramLoginAccount.Status.CODE_SENT,
            phone_code_hash="fake-old-phone-code-hash",
            session_string="fake-old-session",
        )

        def stale_result(*args):
            refreshed = TelegramLoginAccount.objects.get(pk=account.pk)
            refreshed.phone_code_hash = "fake-new-phone-code-hash"
            refreshed.session_string = "fake-new-session"
            refreshed.save()
            return LoginResult(
                requires_password=False,
                session_string="fake-stale-session",
                user=TelegramUserInfo(10001),
            )

        with patch(
            "botcore.views.telegram_account_service.sign_in_with_code",
            side_effect=stale_result,
        ):
            response = self.client.post("/api/telegram-accounts/login/code/", {
                "account_id": account.pk,
                "code": "00000",
            }, format="json")

        self.assertEqual(response.status_code, 409)
        account.refresh_from_db()
        self.assertEqual(account.status, TelegramLoginAccount.Status.CODE_SENT)
        self.assertEqual(account.phone_code_hash_plain, "fake-new-phone-code-hash")
        self.assertEqual(account.session_string_plain, "fake-new-session")

    def test_deleted_account_after_start_network_result_returns_conflict(self):
        def delete_then_succeed(phone):
            TelegramLoginAccount.objects.get(phone=phone).delete()
            return CodeSentResult(
                phone=phone,
                phone_code_hash="fake-phone-code-hash",
                session_string="fake-session-string",
            )

        with patch(
            "botcore.views.telegram_account_service.send_login_code",
            side_effect=delete_then_succeed,
        ):
            response = self.client.post("/api/telegram-accounts/login/start/", {
                "phone": "+12025550100",
            }, format="json")

        self.assertEqual(response.status_code, 409)
        self.assertFalse(TelegramLoginAccount.objects.exists())

    def test_deleted_account_after_start_network_error_returns_conflict(self):
        def delete_then_fail(phone):
            TelegramLoginAccount.objects.get(phone=phone).delete()
            raise TelegramAccountError("无法连接 Telegram，请稍后重试。", code="network_error")

        with patch(
            "botcore.views.telegram_account_service.send_login_code",
            side_effect=delete_then_fail,
        ):
            response = self.client.post("/api/telegram-accounts/login/start/", {
                "phone": "+12025550100",
            }, format="json")

        self.assertEqual(response.status_code, 409)
        self.assertFalse(TelegramLoginAccount.objects.exists())

    def test_deleted_account_after_code_or_password_result_returns_conflict(self):
        cases = [
            (TelegramLoginAccount.Status.CODE_SENT, "login/code", {"code": "00000"}, "sign_in_with_code"),
            (TelegramLoginAccount.Status.PASSWORD_REQUIRED, "login/password", {"password": "fake-secret-password"}, "sign_in_with_password"),
        ]
        for index, (account_status, path, payload, service_name) in enumerate(cases):
            with self.subTest(path=path):
                account = self.create_account(
                    phone=f"+1202555010{index}",
                    status=account_status,
                    phone_code_hash="fake-phone-code-hash" if index == 0 else "",
                    session_string="fake-session-string",
                )

                def delete_then_succeed(*args):
                    TelegramLoginAccount.objects.filter(pk=account.pk).delete()
                    return LoginResult(
                        requires_password=False,
                        session_string="fake-final-session",
                        user=TelegramUserInfo(10001),
                    )

                with patch(
                    f"botcore.views.telegram_account_service.{service_name}",
                    side_effect=delete_then_succeed,
                ):
                    response = self.client.post(
                        f"/api/telegram-accounts/{path}/",
                        {"account_id": account.pk, **payload},
                        format="json",
                    )

                self.assertEqual(response.status_code, 409)
                self.assertFalse(TelegramLoginAccount.objects.filter(pk=account.pk).exists())

    def test_deleted_account_after_code_error_or_check_result_returns_conflict(self):
        code_account = self.create_account(
            status=TelegramLoginAccount.Status.CODE_SENT,
            phone_code_hash="fake-phone-code-hash",
            session_string="fake-session-string",
        )

        def delete_then_code_error(*args):
            TelegramLoginAccount.objects.filter(pk=code_account.pk).delete()
            raise TelegramAccountError("验证码错误，请重新输入。", code="invalid_code")

        with patch(
            "botcore.views.telegram_account_service.sign_in_with_code",
            side_effect=delete_then_code_error,
        ):
            code_response = self.client.post("/api/telegram-accounts/login/code/", {
                "account_id": code_account.pk,
                "code": "00000",
            }, format="json")

        check_account = self.create_account(
            phone="+12025550101",
            status=TelegramLoginAccount.Status.LOGGED_IN,
            session_string="fake-session-string",
        )

        def delete_then_check_result(*args):
            TelegramLoginAccount.objects.filter(pk=check_account.pk).delete()
            return SessionCheckResult(authorized=False)

        with patch(
            "botcore.views.telegram_account_service.check_session",
            side_effect=delete_then_check_result,
        ):
            check_response = self.client.post(
                f"/api/telegram-accounts/{check_account.pk}/check/",
            )

        unauthorized_account = self.create_account(
            phone="+12025550102",
            status=TelegramLoginAccount.Status.LOGGED_IN,
            session_string="fake-session-string",
        )

        def delete_then_unauthorized(*args):
            TelegramLoginAccount.objects.filter(pk=unauthorized_account.pk).delete()
            raise TelegramAccountError(
                "Telegram 会话已失效，请重新登录。",
                code="session_unauthorized",
            )

        with patch(
            "botcore.views.telegram_account_service.check_session",
            side_effect=delete_then_unauthorized,
        ):
            unauthorized_response = self.client.post(
                f"/api/telegram-accounts/{unauthorized_account.pk}/check/",
            )

        self.assertEqual(code_response.status_code, 409)
        self.assertEqual(check_response.status_code, 409)
        self.assertEqual(unauthorized_response.status_code, 409)
        self.assertFalse(TelegramLoginAccount.objects.exists())

    @staticmethod
    def _account_state(account):
        return (
            account.status,
            account.phone_code_hash,
            account.session_string,
            account.login_attempt_id,
            account.login_attempt_started_at,
            account.last_error,
            account.updated_at,
        )


@override_settings(SECRET_KEY="fake-test-secret", CONFIG_ENCRYPTION_KEY="fake-config-key")
class TelegramAccountStartTransactionTests(TransactionTestCase):
    def setUp(self):
        self.client = APIClient()
        self.runtime_preflight = patch(
            "botcore.views.telegram_account_service.validate_runtime_configuration",
        )
        self.runtime_preflight.start()
        self.addCleanup(self.runtime_preflight.stop)

    def test_start_calls_network_outside_atomic_and_blocks_overlapping_same_phone(self):
        overlapping_responses = []

        def send_code(phone):
            self.assertFalse(connection.in_atomic_block)
            TelegramBot.objects.create(
                name="Concurrent database writer",
                token_env_var="CONCURRENT_DATABASE_WRITER_TOKEN",
            )
            overlapping_responses.append(
                self.client.post("/api/telegram-accounts/login/start/", {
                    "phone": phone,
                }, format="json"),
            )
            return CodeSentResult(
                phone=phone,
                phone_code_hash="fake-phone-code-hash",
                session_string="fake-session-string",
            )

        with patch(
            "botcore.views.telegram_account_service.send_login_code",
            side_effect=send_code,
        ) as send:
            response = self.client.post("/api/telegram-accounts/login/start/", {
                "phone": "+12025550100",
            }, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(overlapping_responses[0].status_code, 409)
        self.assertEqual(send.call_count, 1)
        self.assertTrue(TelegramBot.objects.filter(name="Concurrent database writer").exists())

    def test_start_discards_result_when_attempt_was_replaced(self):
        replacement_attempt_id = "replacement-attempt"

        def replace_attempt(phone):
            TelegramLoginAccount.objects.filter(phone=phone).update(
                login_attempt_id=replacement_attempt_id,
            )
            return CodeSentResult(
                phone=phone,
                phone_code_hash="fake-stale-phone-code-hash",
                session_string="fake-stale-session",
            )

        with patch(
            "botcore.views.telegram_account_service.send_login_code",
            side_effect=replace_attempt,
        ):
            response = self.client.post("/api/telegram-accounts/login/start/", {
                "phone": "+12025550100",
            }, format="json")

        self.assertEqual(response.status_code, 409)
        account = TelegramLoginAccount.objects.get()
        self.assertEqual(account.login_attempt_id, replacement_attempt_id)
        self.assertEqual(account.status, TelegramLoginAccount.Status.PENDING)
        self.assertEqual(account.phone_code_hash_plain, "")
        self.assertEqual(account.session_string_plain, "")

    def test_start_takes_over_expired_pending_attempt(self):
        TelegramLoginAccount.objects.create(
            label="Abandoned attempt",
            phone="+12025550100",
            status=TelegramLoginAccount.Status.PENDING,
            login_attempt_id="abandoned-attempt",
            login_attempt_started_at=timezone.now() - timedelta(minutes=3),
        )
        result = CodeSentResult(
            phone="+12025550100",
            phone_code_hash="fake-phone-code-hash",
            session_string="fake-session-string",
        )

        with patch(
            "botcore.views.telegram_account_service.send_login_code",
            return_value=result,
        ) as send:
            response = self.client.post("/api/telegram-accounts/login/start/", {
                "phone": "+12025550100",
            }, format="json")

        self.assertEqual(response.status_code, 200)
        send.assert_called_once_with("+12025550100")
        account = TelegramLoginAccount.objects.get()
        self.assertEqual(account.status, TelegramLoginAccount.Status.CODE_SENT)
        self.assertEqual(account.login_attempt_id, "")
        self.assertIsNone(account.login_attempt_started_at)
