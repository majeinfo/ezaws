'''
Example of use:
$ ./copy_security_groups.py --src-profil SRC --src-region eu-west-1 --dst-profil DST --dst-region eu-central-1 -v

The copied Security Group will be tagged with the key OriginalName and the value will be the original Id
'''
import datetime
import time
import logging

MAX_RESULTS = 200

logger = logging.getLogger('commands')


def copy_security_groups(src_client, dst_client):
    # First we must create all the SecGroups, but empty because SG can refer each other
    # In a second step, we fill the rules
    src_sec_groups = []
    next_token = None
    while True:
        if next_token is None:
            sec_groups_slice = src_client.describe_security_groups(MaxResults=MAX_RESULTS)
        else:
            sec_groups_slice = src_client.describe_security_groups(MaxResults=MAX_RESULTS, NextToken=next_token)

        src_sec_groups += sec_groups_slice['SecurityGroups']

        if 'NextToken' in sec_groups_slice:
            logger.info("MaxResults is too low for describe_security_groups, go on with next_token...")
            next_token = sec_groups_slice['NextToken']
        else:
            break

    for security_group in src_sec_groups:
        print(security_group['GroupName'], security_group['Description'], security_group['VpcId'])




if __name__ == '__main__':
    # standalone & batch mode
    import argparse
    import boto3

    usage = "%(prog)s --src-profile name [--src-region=REGION] --dst-profile name [--dst-region=REGION] [-v|--verbose]"

    parser = argparse.ArgumentParser(
        description="Copy Security Groups from a source account to a destination account",
        usage=usage
    )
    parser.add_argument("--src-profile", nargs='?', help="Name of source profile in .aws/config", required=True)
    parser.add_argument("--src-region", nargs='?', help="Region where the source EBS are located", default=None)
    parser.add_argument("--dst-profile", nargs='?', help="Name of destination profile in .aws/config or .aws/credentials", required=True)
    parser.add_argument("--dst-region", nargs='?', help="Region where the destination EBS must be created", default=None)
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug mode", default=False)
    opts = parser.parse_args()

    if opts.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    logger.addHandler(logging.StreamHandler())

    src_session = boto3.Session(profile_name=opts.src_profile, region_name=opts.src_region) #if opts.src_profile_name else boto3.Session()
    src_client =  src_session.client('ec2')

    dst_session = boto3.Session(profile_name=opts.dst_profile, region_name=opts.dst_region) if opts.dst_profile else boto3.Session(region_name=sopts.dst_region)
    dst_client =  dst_session.client('ec2')

    sec_groups = copy_security_groups(src_client, dst_client)


