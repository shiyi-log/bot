from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("botcore", "0009_secure_telegram_login_account_phone")]

    operations = [
        migrations.AddField(
            model_name="tronaddress",
            name="usdt_balance_sun",
            field=models.BigIntegerField(default=0),
        ),
    ]
