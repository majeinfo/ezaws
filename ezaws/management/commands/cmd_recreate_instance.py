'''
Example fo use:
$ python manage.py cmd_recreate_instance --instance-name MASTER --target-account DFI-BKP --key-pair-name dispofifrankfurt --verbosity 2

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

ALL = "all"

class Command(BaseCommand):
    help = (
        "Recreate an instance from its snapshotted Volumes",
    )

    def add_arguments(self, parser):
        parser.add_argument("--from-version", nargs='?', default='latest', required=False)
        parser.add_argument("--target-account", nargs='?', default="MAJE", required=False)
        parser.add_argument("--instance-name", nargs='?', default=ALL, required=True)
        parser.add_argument("--az", nargs='?', required=False)
        parser.add_argument("--key-pair-name", nargs='?', required=False)

    def handle(self, *args, **options):
        global verbosity
        verbosity = options.get("verbosity", NORMAL)
        instance_name = options.get("instance_name", ALL)
        target_account = options.get("target_account", "MAJE")
        key_pair_name = options.get("key_pair_name", "")

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
            instance_name = instance_name.upper()
            found_snapshots = find_instance_snapshots(client, self.dst_customer.owner_id, instance_name)
            recreate_instance(client, instance_name, found_snapshots, az, key_pair_name)
        except Exception as e:
            std_logger.error(f"Re-creation of instance {instance_name} failed:")
            std_logger.error(e)
