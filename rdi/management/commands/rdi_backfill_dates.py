from django.core.management.base import BaseCommand
from django.db import transaction

from rdi.models import RDIImport
from rdi.services import _import_rdi_csv_file, parse_snapshot_datetime_from_filename


class Command(BaseCommand):
    help = "Backfill (recompute) snapshot_datetime and CSV date fields for all existing RDI imports."

    def handle(self, *args, **options):
        total = RDIImport.objects.count()
        self.stdout.write(f"Backfilling RDI dates for {total} imports...")

        done = 0
        updated_imports = 0
        with transaction.atomic():
            for imp in RDIImport.objects.order_by("id"):
                snapshot_dt = parse_snapshot_datetime_from_filename(imp.original_filename)
                if imp.snapshot_datetime != snapshot_dt:
                    imp.snapshot_datetime = snapshot_dt
                    imp.save(update_fields=["snapshot_datetime"])
                    updated_imports += 1

                # Re-parse the stored CSV file and update RDIRecord fields.
                _import_rdi_csv_file(imp)
                done += 1

        self.stdout.write(self.style.SUCCESS(f"Done. Imports processed: {done}. Snapshot updated: {updated_imports}"))

