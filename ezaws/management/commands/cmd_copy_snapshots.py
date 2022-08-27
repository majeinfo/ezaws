'''
Example of use:
$ python manage.py cmd_copy_snapshots --src-account SRC --src-region eu-west-1 --dst-account DST --dst-region eu-central-1 -v

This script must be launched in the target Account
'''
import logging
from django.core.management.base import BaseCommand
from web.utils import get_customer, get_client
from .recreate_instance import recreate_instance, find_instance_snapshots

std_logger = logging.getLogger('commands')

SILENT, NORMAL, VERBOSE = 0, 1, 2
verbosity = NORMAL

STOP, CONTINUE = 1, 2
on_error = CONTINUE

class Command(BaseCommand):
    help = (
        "Copy snapshots shared by the source account to the target account",
    )

    def add_arguments(self, parser):
        parser.add_argument("--from-version", nargs='?', default='latest', required=False)
        parser.add_argument("--target-account", nargs='?', default="MAJE", required=False)


    def handle(self, *args, **options):
        global verbosity
        verbosity = options.get("verbosity", NORMAL)
        target_account = options.get("target_account", "MAJE")

        if verbosity >= VERBOSE:
            std_logger.setLevel(logging.DEBUG)

        try:
            self.dst_customer = get_customer(target_account)
            az = options.get("az", "")
            if not az:
                az = self.dst_customer.region
        except Exception as e:
            std_logger.error(f"The target account {target_account} does not exist")
            return

        try:
            client = get_client(self.dst_customer, 'ec2')
            # TODO
            std_logger(NotImplemented)
        except Exception as e:
            std_logger.error(f"Copy of snapshots failed:")
            std_logger.error(e)
