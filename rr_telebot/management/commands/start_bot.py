from django.core.management.base import BaseCommand, CommandError
from rr_telebot.async_dispatcher import start
import sentry_sdk



class Command(BaseCommand):
    help = 'Start Telegram Bot dispatcher'

    def add_arguments(self, parser):
        parser.add_argument('--loglevel', type=str)

    def handle(self, *args, **options):
        loglevel = options['loglevel']
        sentry_sdk.init(
            "https://glet_50f538f71aa1a73d0e00ef027887e7a1@gitlab.com/api/v4/error_tracking/collector/33259870",            # Set traces_sample_rate to 1.0 to capture 100%
            # of transactions for performance monitoring.
            # We recommend adjusting this value in production.
            traces_sample_rate=1.0,
        )
        start(loglevel)
