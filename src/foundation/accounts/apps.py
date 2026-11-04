from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "foundation.accounts"
    # Keep the existing migration, content type and database table identities.
    label = "accounts"
    verbose_name = "Contas"
