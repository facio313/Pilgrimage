from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="email_verified",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="user",
            name="sso_link_allowed",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="user",
            name="sso_subject",
            field=models.CharField(blank=True, editable=False, max_length=255, null=True, unique=True),
        ),
        migrations.RunSQL(
            sql="""
                CREATE FUNCTION users_reject_sso_subject_change()
                RETURNS trigger AS $$
                BEGIN
                    IF OLD.sso_subject IS NOT NULL
                       AND NEW.sso_subject IS DISTINCT FROM OLD.sso_subject THEN
                        RAISE EXCEPTION 'users.sso_subject is immutable once set'
                            USING ERRCODE = 'integrity_constraint_violation';
                    END IF;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;

                CREATE TRIGGER users_sso_subject_immutable
                BEFORE UPDATE OF sso_subject ON users
                FOR EACH ROW
                EXECUTE FUNCTION users_reject_sso_subject_change();
            """,
            reverse_sql="""
                DROP TRIGGER IF EXISTS users_sso_subject_immutable ON users;
                DROP FUNCTION IF EXISTS users_reject_sso_subject_change();
            """,
        ),
    ]
