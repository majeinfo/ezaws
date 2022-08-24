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
        "Add tags to snapshots according to the instance description",
    )

    def add_arguments(self, parser):
        '''
        Note: the AWS Region is attached in the DB with the customer account. If you want to
              create resources in another Region, you must define another account
        '''
        parser.add_argument("--target-account", nargs='?', default="MAJE", required=False)
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
            self._tag_volumes(system_tag, volume_tag)
        except Exception as e:
            std_logger.error(f"Tagging failed")
            std_logger.error(e)


    def _tag_volumes(self, system_tag, volume_tag):
        client = get_client(self.dst_customer, 'ec2')

        # Find all instances
        try:
            instances = client.describe_instances(MaxResults=200)
        except Exception as e:
            raise Exception(f"Could not retrieve instances description {e}")

        if 'NextToken' in instances:
            std_logger.info("MaxResults is too low for describe_instances")

        # Build an dict with InstanceId as key
        instance_ids = {}
        for resv in instances['Reservations']:
            instance_ids[resv['Instances'][0]['InstanceId']] = resv['Instances'][0]

        # Find all the volumes that must be snapshotted
        try:
            volumes = client.describe_volumes(MaxResults=200, Filters=[{'Name': f'tag:{volume_tag}', 'Values': ['True']}])
            if 'NextToken' in volumes:
                std_logger.info("MaxResults is too low for describe_volumes")
            std_logger.debug(volumes)
        except Exception as e:
            raise Exception(f"Could not retrieve volumes description {e}")

        for volume in volumes['Volumes']:
            # Add a tag with attachment info
            #print(volume)
            attachments = volume['Attachments'] # TODO: handle only ONE attachment
            if not len(attachments) or attachments[0]['State'] != 'attached':
                std_logger.info(f"Volume {volume['VolumeId']} is not attached")
                continue

            instance_id = attachments[0]['InstanceId']
            volume_id = volume['VolumeId']
            if instance_id not in instance_ids:
                raise Exception(f"No instance found for InstanceId {instance_id} referenced by volume {volume_id}")

            instance = instance_ids[instance_id]
            device = attachments[0]['Device']
            instance_name = self._get_instance_from_id(volume_id, instance_id, instance)
            tags = [
                {'Key': 'Instance', 'Value': instance_name},
                {'Key': 'Device', 'Value': device},
            ]

            # Test if volume is a SYSDISK volume
            for tag in volume['Tags']:
                if tag['Key'] == system_tag:
                    instance_type = instance['InstanceType']
                    tags.append({'Key': 'InstanceType', 'Value': instance_type})
                    tags.append({'Key': 'AvailabilityZone', 'Value': instance['Placement']['AvailabilityZone']})

                    if 'IamInstanceProfile' in instance:
                        iam_profile_arn = instance['IamInstanceProfile']['Arn']
                        iam_profile_id = instance['IamInstanceProfile']['Id']
                        tags.append({'Key': 'IamProfileArn', 'Value': iam_profile_arn})
                        tags.append({'Key': 'IamProfileId', 'Value': iam_profile_id})

                    security_groups = self._linearize(instance['SecurityGroups'])
                    tags.append({'Key': 'SecurityGroups', 'Value': security_groups})
                    break

            client.create_tags(Resources=[volume_id], Tags=tags)


    def _get_instance_from_id(self, volume_id, instance_id, instance):
        for tag in instance['Tags']:
            if tag['Key'] == 'Name':
                return tag['Value']

        raise Exception(f"Instance {instance_id} has no Name tag !")


    def _linearize(self, security_groups):
        sec = ""
        for security_goup in security_groups:
            sec = sec + security_goup['GroupName'] + ':' + security_goup['GroupId'] + ':'

        return sec
