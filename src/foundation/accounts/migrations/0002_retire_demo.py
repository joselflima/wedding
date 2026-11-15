from django.db import migrations


def retire_demo(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Session = apps.get_model("sessions", "Session")
    from django.contrib.sessions.backends.db import SessionStore
    ids = set(str(pk) for pk in User.objects.filter(is_demo=True).values_list("pk", flat=True))
    User.objects.filter(is_demo=True).update(is_active=False, password="!")
    for session in Session.objects.all().iterator():
        if str(SessionStore().decode(session.session_data).get("_auth_user_id")) in ids:
            session.delete()


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial"), ("sessions", "0001_initial")]
    operations = [migrations.RunPython(retire_demo, migrations.RunPython.noop),
                  migrations.RemoveField(model_name="user", name="is_demo")]
