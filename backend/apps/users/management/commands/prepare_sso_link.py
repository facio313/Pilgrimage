import uuid

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import transaction

User = get_user_model()


class Command(BaseCommand):
    help = "Approve exactly one verified local user for a one-time SSO email link."

    def add_arguments(self, parser):
        parser.add_argument("--user-id", required=True)
        parser.add_argument("--verified-email", required=True)

    def handle(self, *args, **options):
        try:
            user_id = uuid.UUID(options["user_id"])
        except (TypeError, ValueError) as exc:
            raise CommandError("--user-id must be a valid UUID.") from exc
        email = options["verified_email"].strip().lower()
        try:
            validate_email(email)
        except ValidationError as exc:
            raise CommandError("--verified-email must be a valid email address.") from exc

        with transaction.atomic():
            matches = list(User.objects.select_for_update().filter(email__iexact=email))
            if len(matches) != 1 or matches[0].pk != user_id:
                raise CommandError("The verified email must identify exactly the requested user.")
            user = matches[0]
            if not user.is_active:
                raise CommandError("An inactive user cannot be prepared for SSO linking.")
            if user.sso_subject is not None:
                raise CommandError("This user already has an SSO subject.")
            user.email_verified = True
            user.sso_link_allowed = True
            user.save(update_fields=["email_verified", "sso_link_allowed"])

        self.stdout.write(self.style.SUCCESS("The user is approved for one SSO link."))
