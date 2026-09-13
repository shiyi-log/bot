from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("botcore", "0010_tronaddress_usdt_balance_sun")]
    operations = [
        migrations.CreateModel(name="TronBlockCursor", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("network", models.CharField(default="mainnet", max_length=32, unique=True)),
            ("next_block", models.BigIntegerField(default=0)),
            ("last_scanned_block", models.BigIntegerField(default=0)),
            ("updated_at", models.DateTimeField(auto_now=True)),
        ]),
        migrations.CreateModel(
            name="TronTransferEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("block_number", models.BigIntegerField(db_index=True)),
                ("block_timestamp", models.DateTimeField(blank=True, null=True)),
                ("tx_id", models.CharField(max_length=128)),
                ("event_index", models.PositiveIntegerField(default=0)),
                ("currency", models.CharField(max_length=16)),
                ("contract_address", models.CharField(blank=True, max_length=34)),
                ("from_address", models.CharField(max_length=34)),
                ("to_address", models.CharField(max_length=34)),
                ("amount_sun", models.BigIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-block_number", "-created_at"],
                "constraints": [models.UniqueConstraint(fields=["tx_id", "event_index"], name="unique_tron_transfer_event")],
            },
        ),
    ]
