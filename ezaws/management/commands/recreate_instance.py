'''
Example of use:
$ ./recreate_instance.py --instance-name MASTER --profile DFI-BKP --subnet-id xyz --verbosity 2

This script must be launched in the target Account
'''
import logging

MAX_RESULTS = 200
ALL = "all"

logger = logging.getLogger('commands')


def find_instance_snapshots(client, account_id, instance_name):
    '''
    Find the snapshots with a tag matching the specified instance name.

    :param client:
    :param account_id:
    :param instance_name:
    :return: liste of instances
    '''
    def _set_instance(tag_value, snapshot):
        nonlocal found_snapshots
        found_snapshots[tag_value] = {
            'SnapshotId': snapshot['SnapshotId'],
            'StartTime': snapshot['StartTime'],
            'Tags': snapshot['Tags'],
        }

    # Find the snapshots that have the instance_name in the Name (tags['Name'])
    snapshots = []
    next_token = None
    while True:
        try:
            if next_token is None:
                snapshots_slice = client.describe_snapshots(MaxResults=MAX_RESULTS, OwnerIds=[account_id])
            else:
                snapshots_slice = client.describe_snapshots(MaxResults=MAX_RESULTS, OwnerIds=[account_id], NextToken=next_token)

            snapshots += snapshots_slice['Snapshots']
        except Exception as e:
            raise Exception(f"Could not retrieve snapshots description {e}")

        if 'NextToken' in snapshots_slice:
            logger.info("MaxResults is too low for describe_snpashots")
            next_token = snapshots_slice['NextToken']
        else:
            break

    found_snapshots = {}
    for snapshot in snapshots:
        logger.debug(f"Found {snapshot['SnapshotId']}")
        if not 'Tags' in snapshot:
            logger.debug("Snapshot discarded because it has no Tag")
            continue

        for tag in snapshot['Tags']:
            if tag['Key'] != 'Name':
                continue

            tag_value = tag['Value'].upper()
            if instance_name == tag_value or tag_value.startswith(instance_name + '-'):
                logger.debug(f"Found snapshot {snapshot['SnapshotId']} for {tag_value}")
                if tag_value not in found_snapshots:
                    _set_instance(tag_value, snapshot)
                else:
                    # In case of duplicated snapshots, take the latest one
                    if snapshot['StartTime'] > found_snapshots[tag_value]['StartTime']:
                        logger.info(f"Newer snapshot found for {tag_value}")
                        _set_instance(tag_value, snapshot)

                break

    return found_snapshots


def recreate_instance(client, account_id, instance_name, snapshots, recreate_ami, region, subnet_id):
    # Check if we found a snapshot for the system
    logger.info(f"Try to recreate instance {instance_name} from its snapshots...")
    if instance_name not in snapshots:
        raise Exception(f"No system snapshot found for instance {instance_name}")

    snapshot = snapshots[instance_name]

    is_sys_disk = _get_tag_value(snapshot, 'SYSDISK')
    device_name = _get_tag_value(snapshot, 'Device')
    instance_type = _get_tag_value(snapshot, 'InstanceType')
    availability_zone = _get_tag_value(snapshot, 'AvailabilityZone')
    architecture = _get_tag_value(snapshot, 'Architecture')

    # Check if a new AMI must be created
    ami = client.describe_images(
        Filters=[{'Name': 'name', 'Values': [instance_name]}],
        Owners=[account_id]
    )

    # Delete existing AMI if needed
    if len(ami['Images']) and recreate_ami:
        client.deregister_image(ImageId=ami['Images'][0]['ImageId'])

    # Create a new AMI if required
    if len(ami['Images']) == 0 or recreate_ami:
        logger.info(f"Create AMI from snapshot {snapshot}")
        ami = client.register_image(
            Architecture=architecture,
            BlockDeviceMappings=[
                {
                    'DeviceName': device_name,
                    'Ebs': {
                        #'DeleteOnTermination': True,
                        'SnapshotId': snapshot['SnapshotId'],
                        #'VolumeSize': 20,
                        #'VolumeType': 'gp2'
                    }
                },
            ],
            #EnaSupport=True,   # TODO: ????
            Description=f"AMI created from Snapshot {snapshot['SnapshotId']}",
            Name=instance_name,
            RootDeviceName=device_name,
            VirtualizationType='hvm'
        )
        logger.info(f"AMI {ami['ImageId']} created")
    else:
        ami = ami['Images'][0]
        logger.info(f"AMI {ami['ImageId']} already exists and must not be recreated")

    # Create an instance from the AMI
    if subnet_id:   # needed for EC2-Classis
        instances = client.run_instances(
            # TODO: BlockDeviceMappings (rend inutile la création des Volumes dans la fonction suivante)
            ImageId=ami['ImageId'],
            MinCount=1,
            MaxCount=1,
            InstanceType=instance_type,
            #Placement={'AvailabilityZone': az + availability_zone[-1]},
            SubnetId=subnet_id,
            SecurityGroups=[],          # TODO: to be filled in
            TagSpecifications=[
                {'ResourceType': 'instance', 'Tags': [{'Key': 'Name', 'Value': instance_name}]}
            ]
        )
    else:
        instances = client.run_instances(
            # TODO: BlockDeviceMappings (rend inutile la création des Volumes dans la fonction suivante)
            ImageId=ami['ImageId'],
            MinCount=1,
            MaxCount=1,
            InstanceType=instance_type,
            Placement={'AvailabilityZone': region + availability_zone[-1]}, # TODO: suppose que la destination a autant de AZ que l'original
            SecurityGroups=[],          # TODO: to be filled in
            TagSpecifications=[
                {'ResourceType': 'instance', 'Tags': [{'Key': 'Name', 'Value': instance_name}]}
            ]
        )

    # TODO: il manque les rôles et la conf réseau (private+public+EIP)
    # TODO: pour créer une instance avec un rôle, il faut une permission IAM PassRole
    logger.info(f"Instance {instances['Instances'][0]['InstanceId']} created")

    _recreate_volumes(client, instance_name, snapshots, region + availability_zone[-1])


def _recreate_volumes(client, instance_name, snapshots, az):
    logger.info(f"Recreate volumes for instance {instance_name}")

    for tag_name, snapshot in snapshots.items():
        if tag_name.upper() == instance_name:
            continue

        logger.info(f"Create a volume from snapshot {snapshot['SnapshotId']} ({tag_name})")
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


def _get_tag_value(snapshot, tag_name):
    for tag in snapshot['Tags']:
        if tag['Key'] == tag_name:
            return tag['Value']

    raise Exception(f"Snapshot {snapshot['SnapshotId']} has no {tag_name} tag")


if __name__ == '__main__':
    # standalone & batch mode
    import argparse
    import boto3

    usage = "%(prog)s --instance-name name [--profile profile_name] [--region region] [-s|--subnet-id subnet] [-a|--recreate-ami] [-v|--verbose]"

    parser = argparse.ArgumentParser(
        description="Recreate an instance from the snapshoted volumes",
        usage=usage
    )
    parser.add_argument("-p", "--profile", nargs='?', help="Name of profile in .aws/config or .aws/credentials", required=True)
    parser.add_argument("-r", "--region", nargs='?', help="Name of the Region where are the snapshots and the instances", required=True)
    parser.add_argument("-i", "--instance-name", nargs='?', help="Name of the Instance to recreate", required=True)
    parser.add_argument("-a", "--recreate-ami", action="store_true", help="Recreate the AMI if it already exists", default=False)
    parser.add_argument("-s", "--subnet-id", nargs='?', help="Subnet ID", default=None)
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug mode", default=False)
    opts = parser.parse_args()

    if opts.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    logger.addHandler(logging.StreamHandler())

    session = boto3.Session(profile_name=opts.profile)
    if opts.region:
        client = session.client('ec2', region_name=opts.region)
    else:
        client = session.client('ec2')

    account_id = session.client('sts').get_caller_identity().get('Account')
    found_snapshots = find_instance_snapshots(client, account_id, opts.instance_name)
    recreate_instance(client, account_id, opts.instance_name, found_snapshots, opts.recreate_ami, opts.region, opts.subnet_id)
    logger.info("Instance recreated")
