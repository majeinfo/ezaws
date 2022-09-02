'''
Example of use:
$ ./target_group_deregister.py --profile name --region eu-west-1 --instance-name name

This script deregisters an instance from all the Target Groups it belongs.
It displays (or returns) the list of the Target Groups found.
'''
import logging
import time


MAX_RESULTS = 200
RETRY_SECONDS = 20

logger = logging.getLogger('commands')


def deregister_from_target_groups(elbv2_client, ec2_client, instance_name):
    found_groups = []

    # Check if the instance_name exists
    instances = ec2_client.describe_instances(Filters=[{'Name': 'tag:Name', 'Values': [instance_name]}])
    if len(instances['Reservations']) == 0:
        raise Exception(f"Instance {instance_name} not found")

    instance_id = instances['Reservations'][0]['Instances'][0]['InstanceId']

    # TODO: we suppose there are less than MAX_RESULTS Target Groups
    target_groups = elbv2_client.describe_target_groups(
        PageSize=MAX_RESULTS
    )

    if 'TargetGroups' not in target_groups:
        logger.debug("No Target Group found")
        return found_groups

    for target_group in target_groups['TargetGroups']:
        target_group_name = target_group['TargetGroupName']
        logger.debug(f"Examine Target Group {target_group_name}")
        if target_group['TargetType'] != 'instance':
            logger.debug(f"Target Group {target_group_name} is not an Instance Group")
            continue

        # Call the target_health to get the registered instances list
        health = elbv2_client.describe_target_health(
            TargetGroupArn=target_group['TargetGroupArn'],
            Targets=[{'Id': instance_id}]
        )
        logger.debug("describe_target_health=>")
        logger.debug(health)
        if 'TargetHealthDescriptions' not in health or len(health['TargetHealthDescriptions']) == 0:
            continue

        # if health['TargetHealthDescriptions'][0]['TargetHealth']['State'] == 'unused':
        #     continue

        logger.info(f"Deregister from Target Group {target_group_name}")
        response = elbv2_client.deregister_targets(
            TargetGroupArn=target_group['TargetGroupArn'],
            Targets=[{'Id': instance_id}]
        )

        found_groups.append({
            'target_name': target_group_name,
            'target_arn': target_group['TargetGroupArn']
        })

    # We must now wait until all the deregistered actions are finsihed (in case of draining)
    in_progress = True
    while in_progress:
        in_progress = False

        for group in found_groups:
            health = elbv2_client.describe_target_health(
                TargetGroupArn=group['target_arn'],
                Targets=[{'Id': instance_id}]
            )
            if 'TargetHealthDescriptions' in health and len(health['TargetHealthDescriptions']) and health['TargetHealthDescriptions'][0]['TargetHealth']['State'] != 'unused':
                logger.info(f"Still draining in Group {group['target_name']}")
                in_progress = True

        if in_progress:
            time.sleep(RETRY_SECONDS)

    return found_groups


if __name__ == '__main__':
    # standalone & batch mode
    import argparse
    import boto3

    usage = "%(prog)s [-p|--profile name] [-r|--region=REGION] -i|--instance-name name [-v|--verbose]"

    parser = argparse.ArgumentParser(
        description="Deregister an instance from all the Target Groups",
        usage=usage
    )
    parser.add_argument("-p", "--profile", nargs='?', help="Name of profile in .aws/config")
    parser.add_argument("-r", "--region", nargs='?', help="Region where the Instance is located", default=None)
    parser.add_argument("-i", "--instance-name", nargs='?', help="Instance name", required=True)
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

    found_groups = deregister_from_target_groups(elbv2_client, ec2_client, opts.instance_name)
    if found_groups:
        logger.info(f"Instance {opts.instance_name} deregistered from all Target Groups")
        logger.info(f"{found_groups}")
