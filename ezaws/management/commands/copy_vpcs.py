'''
Example of use:
$ ./copy_vpc.py --src-profil SRC --src-region eu-west-1 --dst-profil DST --dst-region eu-central-1 --vpc-id xxx -v

The copied VPC will be tagged with the key OriginalName and the value will be the original Id
'''
import datetime
import time
import logging

MAX_RESULTS = 200
VPC_SRC_TAG = 'SourceVpcId'
DHCP_OPTIONS_SRC_TAG = 'SourceDhcpOptionsId'

logger = logging.getLogger('commands')


def copy_vpcs(src_client, dst_client, vpc_id):
    src_vpcs = []
    next_token = None
    while True:
        if next_token is None:
            vpcs_slice = src_client.describe_vpcs(MaxResults=MAX_RESULTS)
        else:
            vpcs_slice = src_client.describe_vpcs(MaxResults=MAX_RESULTS, NextToken=next_token)

        src_vpcs += vpcs_slice['Vpcs']

        if 'NextToken' in vpcs_slice:
            logger.info("MaxResults is too low for describe_vpcs, go on with next_token...")
            next_token = vpcs_slice['NextToken']
        else:
            break

    dst_vpcs = []
    next_token = None
    while True:
        if next_token is None:
            vpcs_slice = dst_client.describe_vpcs(MaxResults=MAX_RESULTS)
        else:
            vpcs_slice = dst_client.describe_vpcs(MaxResults=MAX_RESULTS, NextToken=next_token)

        dst_vpcs += vpcs_slice['Vpcs']

        if 'NextToken' in vpcs_slice:
            logger.info("MaxResults is too low for describe_vpcs, go on with next_token...")
            next_token = vpcs_slice['NextToken']
        else:
            break

    # Must also recreate the ACL, Dhcp Options and route table
    #_create_dhcp_options(src_client, dst_client)

    for src_vpc in src_vpcs:
        if vpc_id is not None and vpc_id != src_vpc['VpcId']:
            continue

        logger.info(f"{src_vpc['VpcId']}, {src_vpc['CidrBlock']}")
        _create_vpc(src_client, dst_client, src_vpc, dst_vpcs)


def _create_vpc(src_client, dst_client, src_vpc, dst_vpcs):
    # Check if VPC already created in destination
    logger.info(f"Check if VPC {src_vpc['VpcId']} must be recreated")

    # Skip default
    if src_vpc['IsDefault']:
        logger.info("skip default VPC")

    for dst_vpc in dst_vpcs:
        if 'Tags' in dst_vpc:
            for tag in dst_vpc['Tags']:
                if tag['Key'] == VPC_SRC_TAG and src_vpc['VpcId'] == tag['Value']:
                    logger.info(f"VPC {src_vpc['VpcId']} already created")
                    return

    # Must copy the src VPC
    # Get the originame Name
    logger.debug(src_vpc)
    src_name = ''
    if 'Tags' in src_vpc:
        for tag in src_vpc['Tags']:
            if tag['Key'] == 'Name':
                src_name = tag['Value']
                break

    vpc = dst_client.create_vpc(
        CidrBlock=src_vpc['CidrBlock'],
        InstanceTenancy=src_vpc['InstanceTenancy'],
        TagSpecifications=[
            {
                'ResourceType': 'vpc',
                'Tags': [
                    {'Key': 'Name', 'Value': src_name},
                    {'Key': VPC_SRC_TAG, 'Value': src_vpc['VpcId']}
                ]
            },
        ]
    )

    # # must copy ACL, route table, DHCP options, subnets
    # src_route = src_client.describe_route_tables(
    #     Filters=[{'Name': 'vpc-id', 'Values': [vpc['VpcId']]}],
    #     MaxResults=100
    # )
    # logger.debug(src_route)
    #
    src_subnets = src_client.describe_subnets(
        Filters=[{'Name': 'vpc-id', 'Values': [src_vpc['VpcId']]}],
        MaxResults=MAX_RESULTS
    )
    logger.debug(src_subnets)

    # TODO: recreate the subnets


def _create_dhcp_options(src_client, dst_client):
    src_dhcp_options = src_client.describe_dhcp_options(
        MaxResults=MAX_RESULTS
    )
    logger.debug(src_dhcp_options)

    dst_dhcp_options = dst_client.describe_dhcp_options(
        MaxResults=MAX_RESULTS
    )
    logger.debug(src_dhcp_options)

    # Loop on the src options and check if they have already been created or not
    for src_opt in src_dhcp_options['DhcpOptions']:
        # Loop in the dest to check if options already created
        for dst_opt in dst_dhcp_options['DhcpOptions']:
            logger.info(dst_opt)


if __name__ == '__main__':
    # standalone & batch mode
    import argparse
    import boto3

    usage = "%(prog)s --src-profile name [--src-region=REGION] --dst-profile name [--dst-region=REGION] [--vpc-id id] [-v|--verbose]"

    parser = argparse.ArgumentParser(
        description="Copy Security Groups from a source account to a destination account",
        usage=usage
    )
    parser.add_argument("--src-profile", nargs='?', help="Name of source profile in .aws/config", required=True)
    parser.add_argument("--src-region", nargs='?', help="Region where the source EBS are located", default=None)
    parser.add_argument("--dst-profile", nargs='?', help="Name of destination profile in .aws/config or .aws/credentials", required=True)
    parser.add_argument("--dst-region", nargs='?', help="Region where the destination EBS must be created", default=None)
    parser.add_argument("--vpc-id", nargs='?', help="Optional VPC Id to recreate from source", default=None)
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug mode", default=False)
    opts = parser.parse_args()

    if opts.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    logger.addHandler(logging.StreamHandler())

    src_session = boto3.Session(profile_name=opts.src_profile, region_name=opts.src_region) #if opts.src_profile_name else boto3.Session()
    src_client =  src_session.client('ec2')

    dst_session = boto3.Session(profile_name=opts.dst_profile, region_name=opts.dst_region) if opts.dst_profile else boto3.Session(region_name=opts.dst_region)
    dst_client =  dst_session.client('ec2')

    sec_groups = copy_vpcs(src_client, dst_client, opts.vpc_id)


