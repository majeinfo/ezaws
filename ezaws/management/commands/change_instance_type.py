'''
Example of use:
$ ./change_instance_type.py --profile name --region eu-west-1 --instance-name --new-type

Change the instance type : it will change and restart the instance
'''
import logging
import time


RETRY_SECONDS = 5

logger = logging.getLogger('commands')


def change_instance_type(ec2_client, instance_name, new_type):
    # Check if the instance_name exists
    instances = ec2_client.describe_instances(Filters=[{'Name': 'tag:Name', 'Values': [instance_name]}])
    if len(instances['Reservations']) == 0:
        raise Exception(f"Instance {instance_name} not found")

    instance_id = instances['Reservations'][0]['Instances'][0]['InstanceId']
    state_name = instances['Reservations'][0]['Instances'][0]['State']['Name']
    if state_name == 'terminated':
        raise Exception("This instance is terminated")

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


if __name__ == '__main__':
    # standalone & batch mode
    import argparse
    import boto3

    usage = "%(prog)s [-p|--profile name] [-r|--region=REGION] -i|--instance-name name -t|--new-type type [-v|--verbose]"

    parser = argparse.ArgumentParser(
        description="Change an instance type",
        usage=usage
    )
    parser.add_argument("-p", "--profile", nargs='?', help="Name of profile in .aws/config")
    parser.add_argument("-r", "--region", nargs='?', help="Region where the Instance is located", default=None)
    parser.add_argument("-i", "--instance-name", nargs='?', help="Instance name", required=True)
    parser.add_argument("-t", "--new-type", nargs='?', help="New Type", required=True)
    parser.add_argument("-v", "--verbose", action="store_true", dest="verbose", help="Debug mode", default=False)
    opts = parser.parse_args()

    if opts.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    logger.addHandler(logging.StreamHandler())

    session = boto3.Session(profile_name=opts.profile) if opts.profile else boto3.Session()
    ec2_client =  session.client('ec2', region_name=opts.region) if opts.region else session.client('ec2')

    result = change_instance_type(ec2_client, opts.instance_name, opts.new_type)
    if result:
        logger.info(f"Instance Type for {opts.instance_name} has been succesfully changed")

