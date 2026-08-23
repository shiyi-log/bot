import re
import unicodedata

from django.db import migrations, models


def _normalize_phone(value):
    normalized = unicodedata.normalize("NFKC", str(value or ""))
    normalized = re.sub(r"[\s().-]+", "", normalized)
    if normalized.startswith("00"):
        normalized = f"+{normalized[2:]}"
    if not re.fullmatch(r"\+[1-9][0-9]{7,14}", normalized):
        return ""
    return normalized


def _account_rank(account):
    has_session = bool((account.session_string or "").strip())
    is_logged_in = account.status == "logged_in"
    return (
        is_logged_in and has_session,
        has_session,
        is_logged_in,
        account.updated_at,
        account.pk,
    )


def clean_telegram_login_accounts(apps, schema_editor):
    account_model = apps.get_model("botcore", "TelegramLoginAccount")
    accounts_by_phone = {}
    for account in account_model.objects.all().iterator():
        normalized_phone = _normalize_phone(account.phone)
        if not normalized_phone:
            account.delete()
            continue
        accounts_by_phone.setdefault(normalized_phone, []).append(account)

    merge_fields = [
        "label",
        "telegram_id",
        "username",
        "first_name",
        "last_name",
        "last_error",
    ]
    for phone, accounts in accounts_by_phone.items():
        ranked_accounts = sorted(accounts, key=_account_rank, reverse=True)
        winner = ranked_accounts[0]
        updates = {"phone": phone}
        for field_name in merge_fields:
            current_value = getattr(winner, field_name)
            if current_value not in (None, ""):
                continue
            for candidate in ranked_accounts[1:]:
                candidate_value = getattr(candidate, field_name)
                if candidate_value not in (None, ""):
                    updates[field_name] = candidate_value
                    break
        checked_values = [
            account.last_checked_at
            for account in ranked_accounts
            if account.last_checked_at is not None
        ]
        if checked_values:
            updates["last_checked_at"] = max(checked_values)
        account_model.objects.filter(pk=winner.pk).update(**updates)
        account_model.objects.filter(
            pk__in=[account.pk for account in ranked_accounts[1:]],
        ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("botcore", "0008_telegramloginaccount_botsettings_telegram_api_hash_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="telegramloginaccount",
            name="login_attempt_id",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name="telegramloginaccount",
            name="login_attempt_started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(clean_telegram_login_accounts, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="telegramloginaccount",
            name="phone",
            field=models.CharField(max_length=32, unique=True),
        ),
        migrations.AddConstraint(
            model_name="telegramloginaccount",
            constraint=models.CheckConstraint(
                condition=~models.Q(phone=""),
                name="telegram_login_account_phone_not_blank",
            ),
        ),
    ]
