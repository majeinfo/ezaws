import logging
from django.core.management.base import BaseCommand
from web.utils import get_customer, get_client
from .tag_volumes import tag_volumes

std_logger = logging.getLogger('commands')

SILENT, NORMAL, VERBOSE = 0, 1, 2
verbosity = NORMAL

STOP, CONTINUE = 1, 2
on_error = CONTINUE

ALL = "all"

class Command(BaseCommand):
    help = (
        "Add tags to snapshots according to the instance description",
    )

    def add_arguments(self, parser):
        '''
        Note: the AWS Region is attached in the DB with the customer account. If you want to
              create resources in another Region, you must define another account
        '''
        parser.add_argument("--target-account", nargs='?', required=True)
        parser.add_argument("--system-tag", nargs='?', default='SYSDISK', required=False)
        parser.add_argument("--volume-tag", nargs='?', default='MUSTSNAP', required=False)

    def handle(self, *args, **options):
        global verbosity
        verbosity = options.get("verbosity", NORMAL)
        target_account = options.get("target_account", "MAJE")
        system_tag = options.get("system_tag", "SYSDISK")
        volume_tag = options.get("volume_tag", "MUSTSNAP")

        if verbosity >= VERBOSE:
            std_logger.setLevel(logging.DEBUG)

        try:
            self.dst_customer = get_customer(target_account)
        except Exception as e:
            std_logger.error(f"The target account {target_account} does not exist")
            return

        try:
            client = get_client(self.dst_customer, 'ec2')
            tag_volumes(client, system_tag, volume_tag)
        except Exception as e:
            std_logger.error(f"Tagging failed")
            std_logger.error(e)
