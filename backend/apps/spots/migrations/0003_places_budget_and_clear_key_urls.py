from django.db import migrations, models


def clear_key_urls(apps, schema_editor):
    apps.get_model("spots", "GooglePlaceCache").objects.using(schema_editor.connection.alias).exclude(
        photo_url="",
    ).update(photo_url="")


class Migration(migrations.Migration):
    dependencies = [("spots", "0002_google_place_cache")]

    operations = [
        migrations.CreateModel(
            name="GooglePlacesBudget",
            fields=[("id", models.PositiveSmallIntegerField(default=1, editable=False, primary_key=True, serialize=False))],
        ),
        migrations.CreateModel(
            name="GooglePlacesCharge",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("operation", models.CharField(max_length=20)),
                ("reserved_krw", models.PositiveIntegerField()),
                ("reserved_at", models.DateTimeField(db_index=True)),
            ],
        ),
        # Deliberately never restore credential-bearing URLs during a rollback.
        migrations.RunPython(clear_key_urls, migrations.RunPython.noop),
    ]
