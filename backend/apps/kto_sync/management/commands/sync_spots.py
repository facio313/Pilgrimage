from django.core.management.base import BaseCommand

from apps.kto_sync.services import sync_spots


class Command(BaseCommand):
    help = "Sync tourist spots from KTO OpenAPI (KorService2/areaBasedList2)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--content-type",
            type=int,
            action="append",
            dest="content_type_ids",
            default=None,
            help="contentTypeId to sync. Repeat for multiple. Default: all from THEME_CONTENT_TYPE_MAP.",
        )
        parser.add_argument(
            "--num-of-rows",
            type=int,
            default=100,
            help="numOfRows per page (default: 100).",
        )
        parser.add_argument(
            "--max-pages",
            type=int,
            default=None,
            help="Cap pages per contentTypeId (default: no cap).",
        )

    def handle(self, *args, **options):
        total = sync_spots(
            content_type_ids=options["content_type_ids"],
            num_of_rows=options["num_of_rows"],
            max_pages=options["max_pages"],
        )
        self.stdout.write(self.style.SUCCESS(f"Synced {total} spots"))
