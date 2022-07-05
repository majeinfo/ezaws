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
EZAWS_KEY = "EZAWS"
EZAWS_VALUE = f"Created at {datetime.now()}"

matchings = {
    'security_group' : {},
}
vpc_id = None

class Command(BaseCommand):
    help = (
        "Copy configuration objects stored in database to an AWS Account"
    )

    def add_arguments(self, parser):
        parser.add_argument("--source-account", nargs='?')
        parser.add_argument("--from-version", nargs='?', default='latest', required=False)
        parser.add_argument("--target-account", nargs='?', default="MAJE", required=False)
        parser.add_argument("--object-type", nargs='?', default="all", required=False)

    def handle(self, *args, **options):
        global verbosity
        verbosity = options.get("verbosity", NORMAL)
        object_type = options.get("object_type", ALL)
        source_account = options["source_account"]
        target_account = options.get("target_account", "MAJE")

        if verbosity >= VERBOSE:
            std_logger.setLevel(logging.DEBUG)

        try:
            src_customer = get_customer(source_account)
        except Exception as e:
            std_logger.error(f"The source account {source_account} does not exist")
            return

        try:
            dst_customer = get_customer(target_account)
        except Exception as e:
            std_logger.error(f"The target account {target_account} does not exist")
            return

        std_logger.info("Start creation")
        # TODO: check the wanted revision/version
        _create_objects(src_customer, dst_customer, object_type)
        _display_created_objects()
        std_logger.info("End creation")

def _create_objects(src_customer, dst_customer, object_type):
    if object_type == ALL or object_type == "security_group":
        _create_security_groups(src_customer, dst_customer)

    if object_type == ALL or object_type == "instance":
        _create_instances(src_customer, dst_customer)

def _create_security_groups(src_customer, dst_customer):
    global matchings

    _ensure_vpc_id(dst_customer)
    security_groups = _get_objects(src_customer, "security_group")
    client = get_client(dst_customer, 'ec2')

    # TODO: il faut supprimer les anciens sg configurés par les nouveaux quand ils sont référencés
    for security_group in security_groups:
        # Skip "default" name
        sec = json.loads(security_group.object_value)
        if sec["GroupName"] != "default":
            try:
                response = client.create_security_group(
                    Description=sec['Description'],
                    GroupName=sec['GroupName'],
                    VpcId=vpc_id,
                    TagSpecifications=_get_ezaws_tag('security-group')
                )
                new_sec_group_id = response['GroupId']
                matchings['security_group'][sec['GroupId']] = new_sec_group_id
                std_logger.info(f"Security group {new_sec_group_id} created")
            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == 'InvalidGroup.Duplicate':
                    std_logger.info(f"Security group {sec['GroupName']} already exists")
                    target_client = get_client(dst_customer, 'ec2')
                    try:
                        target_sec_groups = target_client.describe_security_groups()
                        for target_sec_group in target_sec_groups['SecurityGroups']:
                            if target_sec_group['GroupName'] == sec['GroupName']:
                                new_sec_group_id = target_sec_group['GroupId']
                    except Exception as e:
                        std_logger.error(f'Failed to get security groups of customer {dst_customer.name}')
                        std_logger.error(e)
                        raise e
                else:
                    std_logger.error(e)
                    raise e
        else:
            new_sec_group_id = _get_default_security_group(dst_customer, vpc_id)
            continue    # actually do not try to recreate the default security group

        if 'IpPermissions' in sec:
            try:
                response = client.authorize_security_group_ingress(
                    GroupId=new_sec_group_id,
                    IpPermissions=sec['IpPermissions']
                )
            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == 'InvalidPermission.Duplicate':
                    pass
                else:
                    std_logger.error(e)
                    raise e

        if 'IpPermissionsEgress' in sec:
            try:
                response = client.authorize_security_group_egress(
                    GroupId=new_sec_group_id,
                    IpPermissions=sec['IpPermissionsEgress']
                )
            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == 'InvalidPermission.Duplicate':
                    pass
                else:
                    std_logger.error(e)
                    raise e

def _create_instances(src_customer, dst_customer):
    global matchings

def _display_created_objects():
    std_logger.info("Created objects:")
    std_logger.info(matchings)

def _get_objects(customer, object_type, date=None):
    # TODO: must take the date or latest version in account
    objects = Infrastructure.objects.filter(customer=customer, object_type=object_type).order_by('date')
    return objects

def _ensure_vpc_id(dst_customer):
    global vpc_id

    if not vpc_id:
        vpc_id = input('Default VPC id: ')

        # Check the VPC existence
        client = get_client(dst_customer, 'ec2')
        vpcs = client.describe_vpcs()
        found = False
        for vpc in vpcs['Vpcs']:
            if vpc_id == vpc['VpcId']:
                found = True
                break

            if vpc_id == "default" and vpc['IsDefault']:
                found = True
                vpc_id = vpc['VpcId']
                std_logger.info(f"Default VPC is {vpc_id}")
                break

        if not found:
            std_logger.error(f"VPC id {vpc_id} not found")
            exit(1)

def _get_default_security_group(dst_customer, vpc_id):
    client = get_client(dst_customer, 'ec2')
    sec_groups = client.describe_security_groups(
        Filters=[
            {'Name': 'group-name', 'Values': ['default']},
            {'Name': 'vpc-id', 'Values': [vpc_id]},
        ])

    return sec_groups['SecurityGroups'][0]['GroupId']

def _get_ezaws_tag(resource_type):
    return [{'ResourceType': resource_type, 'Tags': [{'Key': EZAWS_KEY, 'Value': EZAWS_VALUE}]}]