'''
Example of use:
$ ./change_instance_type_in_elb.py --profile name --region eu-west-1 --instance-name --new-type

Change the instance type : it will change the type and restart the instance
But it deregisters the instance from Target Groups and re-registers it at the end
'''
import logging
import time
from change_instance_type import change_instance_type
from target_group_register import register_to_target_groups
from target_group_deregister import deregister_from_target_groups


RETRY_SECONDS = 5

logger = logging.getLogger('commands')




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
    elbv2_client =  session.client('elbv2', region_name=opts.region) if opts.region else session.client('elbv2')
    ec2_client =  session.client('ec2', region_name=opts.region) if opts.region else session.client('ec2')

    found_groups = deregister_from_target_groups(elbv2_client, ec2_client, opts.instance_name)
    if found_groups:
        logger.info(f"Instance {opts.instance_name} deregistered from all Target Groups")
        logger.info(f"{found_groups}")

    result = change_instance_type(ec2_client, opts.instance_name, opts.new_type)
    if result:
        logger.info(f"Instance Type for {opts.instance_name} has been succesfully changed")

        if len(found_groups):
            answer = input(f"Do you want to register {opts.instance_name} in these Target Groups: {found_groups} ? (y/n) ")
            if answer != "y": exit(0)
            result = register_to_target_groups(elbv2_client, ec2_client, opts.instance_name, found_groups)
            if result:
                logger.info(f"Instance {opts.instance_name} registered in all Target Groups")

