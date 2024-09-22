'''
Example of use:
$ ./change_instance_type.py --profile name --region eu-west-1 --instance-name name -t new-type

Change the instance type : it will change and restart the instance
'''
import logging
import time
import re


RETRY_SECONDS = 5

logger = logging.getLogger('commands')


def _change_one_instance_type(ec2_client, instance_name, instance_id, state_name, new_type, dry_run=False):
    if state_name == 'terminated':
        #raise Exception("This instance is terminated")
        logger.info(f"Instance {instance_name} is Terminated")
        return False

    if dry_run:
        logger.info(f"Instance {instance_name} should be impacted")
        return True

    should_be_restarted = state_name == 'running'

    while state_name != 'stopped':
        logger.info(f"Stopping Instance {instance_name} (state is {state_name})")
        response = ec2_client.stop_instances(
            InstanceIds=[instance_id]
        )
        state_name = response['StoppingInstances'][0]['CurrentState']['Name']
        if state_name != 'stopped':
            time.sleep(RETRY_SECONDS)

    logger.info(f"Instance {instance_name} stopped")

    # Change the instance type
    response = ec2_client.modify_instance_attribute(
        InstanceId=instance_id,
        InstanceType={'Value': new_type},
    )
    logger.info(f"Instance Type changed")
    logger.debug(response)

    # Restart the instance if it was previously started
    if should_be_restarted:
        state_name = 'stopped'
        while state_name != 'running':
            logger.info(f"Starting Instance {instance_name} (state is {state_name})")
            response = ec2_client.start_instances(
                InstanceIds=[instance_id]
            )
            state_name = response['StartingInstances'][0]['CurrentState']['Name']
            if state_name != 'running':
                time.sleep(RETRY_SECONDS)

        logger.info(f"Instance {instance_name} running")

    return True


def change_instance_type(ec2_client, instance_name, new_type, dry_run=False):
    # Check if the instance_name exists
    instances = ec2_client.describe_instances(Filters=[{'Name': 'tag:Name', 'Values': [instance_name]}])
    logger.debug(instances)
    if len(instances['Reservations']) == 0:
        raise Exception(f"Instance {instance_name} not found")

    for rsv in instances['Reservations']:
        instance_id = rsv['Instances'][0]['InstanceId']
        state_name = rsv['Instances'][0]['State']['Name']
        instance_name = 'unknown'
        for tag in rsv['Instances'][0]['Tags']:
            if tag['Key'] == 'Name':
                instance_name = tag['Value']
                break

        _change_one_instance_type(ec2_client, instance_name, instance_id, state_name, new_type, dry_run)

    return True


if __name__ == '__main__':
    # standalone & batch mode
    import argparse
    import boto3

    usage = "%(prog)s [-p|--profile name] [-r|--region=REGION] -i|--instance-name name(s) -t|--new-type type [-v|--verbose] [-n|--dry-run]"

    parser = argparse.ArgumentParser(
        description="Change an instance type",
        usage=usage
    )
    parser.add_argument("-p", "--profile", nargs='?', help="Name of profile in .aws/config")
    parser.add_argument("-r", "--region", nargs='?', help="Region where the Instance is located", default=None)
    parser.add_argument("-i", "--instance-name", nargs='?', help="Instance name(s)", required=True)
    parser.add_argument("-t", "--new-type", nargs='?', help="New Type", required=True)
    parser.add_argument("-v", "--verbose", action="store_true", dest="verbose", help="Debug mode", default=False)
    parser.add_argument("-n", "--dry-run", action="store_true", dest="dry_run", help="Dry run mode", default=False)
    opts = parser.parse_args()

    if opts.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    logger.addHandler(logging.StreamHandler())

    session = boto3.Session(profile_name=opts.profile) if opts.profile else boto3.Session()
    ec2_client =  session.client('ec2', region_name=opts.region) if opts.region else session.client('ec2')

    result = change_instance_type(ec2_client, opts.instance_name, opts.new_type, opts.dry_run)
    if result:
        logger.info(f"Instance Type for {opts.instance_name} has been succesfully changed")

