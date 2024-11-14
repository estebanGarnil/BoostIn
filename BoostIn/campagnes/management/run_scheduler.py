# myapp/management/commands/run_scheduler.py
from django.core.management.base import BaseCommand
from campagnes.ecouteur_message import run_scheduler  # Assurez-vous que run_scheduler est bien défini

class Command(BaseCommand):
    help = 'Lance le processus du scheduler'

    def handle(self, *args, **options):
        run_scheduler()
