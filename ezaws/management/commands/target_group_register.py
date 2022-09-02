'''
Example of use:
$ ./target_group_register.py --profile name --region eu-west-1 --instance-name name --target-groups grp1,grp2

This script registers an instance in all the Target Groups specified.
'''
import logging
import time


MAX_RESULTS = 200
RETRY_SECONDS = 20

logger = logging.getLogger('commands')


def register_to_target_groups(elbv2_client, ec2_client, instance_name, target_groups):
    # Check if the instance_name exists
    instances = ec2_client.describe_instances(Filters=[{'Name': 'tag:Name', 'Values': [instance_name]}])
    if len(instances['Reservations']) == 0:
        raise Exception(f"Instance {instance_name} not found")

    instance_id = instances['Reservations'][0]['Instances'][0]['InstanceId']

    # Loop on target group and register the instance
    for target_group_name in target_groups.split(','):
        logger.info(f"Register in Target Group {target_group_name}")

        try:
            target_groups = elbv2_client.describe_target_groups(
                Names=[target_group_name]
            )
        except Exception as e:
            logger.error(f"Target Group {target_group_name} not found")
            raise e

        response = elbv2_client.register_targets(
            TargetGroupArn=target_groups['TargetGroups'][0]['TargetGroupArn'],
            Targets=[{'Id': instance_id}]
        )

    return True


if __name__ == '__main__':
    # standalone & batch mode
    import argparse
    import boto3

    usage = "%(prog)s [-p|--profile name] [-r|--region=REGION] -i|--instance-name name -t|--target-groups grp,... [-v|--verbose]"

    parser = argparse.ArgumentParser(
        description="Register an instance in all the Target Groups",
        usage=usage
    )
    parser.add_argument("-p", "--profile", nargs='?', help="Name of profile in .aws/config")
    parser.add_argument("-r", "--region", nargs='?', help="Region where the Instance is located", default=None)
    parser.add_argument("-i", "--instance-name", nargs='?', help="Instance name", required=True)
    parser.add_argument("-t", "--target-groups", nargs='?', help="Target Group name list (comma separated)", required=True)
    parser.add_argument("-v", "--verbose", action="store_true", dest="verbose", help="Debug mode", default=False)
    opts = parser.parse_args()

    if opts.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    logger.addHandler(logging.StreamHandler())

    session = boto3.Session(profile_name=opts.profile) if opts.profile else boto3.Session()
    elbv2_client =  session.client('elbv2', region_name=opts.region) if opts.region else session.client('elbv2')
    ec2_client =  session.client('ec2', region_name=opts.region) if opts.region else session.client('ec2')

    result = register_to_target_groups(elbv2_client, ec2_client, opts.instance_name, opts.target_groups)
    if result:
        logger.info(f"Instance {opts.instance_name} registered in all Target Groups")
