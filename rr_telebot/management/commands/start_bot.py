from django.core.management.base import BaseCommand, CommandError
from rr_telebot.async_dispatcher import start


class Command(BaseCommand):
    help = 'Start Telegram Bot dispatcher'

    def add_arguments(self, parser):
        parser.add_argument('--loglevel', type=str)

    def handle(self, *args, **options):
        loglevel = options['loglevel']
        start(loglevel)
