'''
Example fo use:
recreate_instance --instance-name MASTER --target-account DFI-BKP --key-pair-name dispofifrankfurt --verbosity 2
'''
import json
import sys
import logging
from datetime import datetime
from web import log

import boto3
import botocore.exceptions
from django.core.management.base import BaseCommand
from web.models import Customer, Infrastructure
from web.utils import get_customers, get_customer, get_client, get_session

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
        '''
        Note: la région est associée au compte. Si on veut copier dans une nouvelle région
              il faut créer un nouveau compte dans l'outil
        '''
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
        instance_name = options.get("instance_name", ALL)
        key_pair_name = options.get("key_pair_name", "")

        if verbosity >= VERBOSE:
            std_logger.setLevel(logging.DEBUG)

        try:
            self.dst_customer = get_customer(target_account)
            az = options.get("az", "")
            if not az:
                az = self.dst_customer.region + "a"
        except Exception as e:
            std_logger.error(f"The target account {target_account} does not exist")
            return

        try:
            instance_name = instance_name.upper()
            snapshots = self._find_instance_snapshots(instance_name)
            self._recreate_instance(instance_name, snapshots, az, key_pair_name)
            self._recreate_volumes(instance_name, snapshots, az)
        except Exception as e:
            std_logger.error(f"Re-creation of instance {instance_name} failed:")
            std_logger.error(e)


    def _find_instance_snapshots(self, instance_name):
        def _set_instance(tag_value, snapshot):
            nonlocal found_snapshots
            found_snapshots[tag_value] = {
                'SnapshotId': snapshot['SnapshotId'],
                'StartTime': snapshot['StartTime'],
                'Tags': snapshot['Tags'],
            }

        # Find the snapshots that have the instance_name in the Name (tags['Name'])
        client = get_client(self.dst_customer, 'ec2')
        try:
            snapshots = client.describe_snapshots(MaxResults=200, OwnerIds=[self.dst_customer.owner_id])
        except Exception as e:
            raise Exception(f"Could not retrieve snapshots description {e}")

        found_snapshots = {}
        for snapshot in snapshots['Snapshots']:
            std_logger.debug(f"{snapshot['SnapshotId']}")
            for tag in snapshot['Tags']:
                if tag['Key'] != 'Name':
                    continue

                tag_value = tag['Value'].upper()
                if instance_name == tag_value or tag_value.startswith(instance_name + '-'):
                    std_logger.debug(f"found snapshot {snapshot['SnapshotId']} for {tag_value}")
                    if tag_value not in found_snapshots:
                        _set_instance(tag_value, snapshot)
                    else:
                        # In case of duplicated snapshots, take the latest one
                        if snapshot['StartTime'] > found_snapshots[tag_value]['StartTime']:
                            std_logger.info(f"Newer snapshot found for {tag_value}")
                            _set_instance(tag_value, snapshot)

                    break

        return found_snapshots


    def _recreate_instance(self, instance_name, snapshots, az, key_pair_name):
        def _is_sys_disk(snapshot):
            for tag in snapshot['Tags']:
                if tag['Key'] == 'SYSDISK':
                    return True

            return False

        def _get_sys_disk_name(snapshot):
            for tag in snapshot['Tags']:
                if tag['Key'] == 'SYSDISKNAME':
                    return tag['Value']

            return None

        # Check we found a snapshot for the system
        std_logger.info(f"Try to recreate instance {instance_name} from its snapshots...")
        if instance_name not in snapshots:
            raise Exception(f"No system snapshot found for instance {instance_name}")

        snapshot = snapshots[instance_name]
        if not _is_sys_disk(snapshot):
            raise Exception(f"Snapshot {snapshot['SnapshotId']} is not a snapshot of a SYSDISK")

        # TODO: ce tag ne sert peut-être à rien car /dev/sda1 est automatiquement converti en /dev/xvda1
        sys_disk_name = _get_sys_disk_name(snapshot)
        if sys_disk_name is None:
            raise Exception(f"Snapshot {snapshot['SnapshotId']} has no SYSDISKNAME tag")

        std_logger.info(f"Create AMI from snapshot {snapshot}")
        client = get_client(self.dst_customer, 'ec2')
        ami = client.register_image(
            BlockDeviceMappings=[
                {
                    'DeviceName': sys_disk_name,
                    'Ebs': {
                        #'DeleteOnTermination': True,
                        'SnapshotId': snapshot['SnapshotId'],
                        #'VolumeSize': 20,
                        #'VolumeType': 'gp2'
                    }
                },
            ],
            #EnaSupport=True,   # TODO: ?
            Description=f"AMI created from Snapshot {snapshot['SnapshotId']}",
            Name=instance_name,
            RootDeviceName=sys_disk_name,
            VirtualizationType='hvm'
        )
        std_logger.info(f"AMI {ami['ImageId']} created")

        # Create an instance from the AMI
        instances = client.run_instances(
            # TODO: BlockDeviceMappings (rend inutile la création des Volumes dans la fonction suivante)
            ImageId=ami['ImageId'],
            MinCount=1,
            MaxCount=1,
            InstanceType="t2.micro",    # TODO: should be the same as the original
            Placement={'AvailabilityZone': az},
            SecurityGroups=[],          # TODO: fill in
            KeyName=key_pair_name,
            TagSpecifications=[
                {'ResourceType': 'instance', 'Tags': [{'Key': 'Name', 'Value': instance_name}]}
            ]
        )
        # TODO: il manque les rôles et la conf réseau (private+public+EIP)
        std_logger.info(f"Instance {instances['Instances'][0]['InstanceId']} created")


    def _recreate_volumes(self, instance_name, snapshots, az):
        std_logger.info(f"Recreate volumes for instance {instance_name}")
        client = get_client(self.dst_customer, 'ec2')

        for tag_name, snapshot in snapshots.items():
            if tag_name.upper() == instance_name:
                continue

            std_logger.info(f"Create a volume from snapshot {snapshot['SnapshotId']} ({tag_name})")
            client.create_volume(
                AvailabilityZone=az,
                SnapshotId=snapshot['SnapshotId'],
                TagSpecifications=[{
                    'ResourceType': 'volume',
                    'Tags': [
                        {'Key': 'Name', 'Value': tag_name},
                    ]
                }]
            )

        return True
