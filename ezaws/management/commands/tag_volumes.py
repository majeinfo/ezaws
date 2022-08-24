import logging

MAX_RESULTS = 5

std_logger = logging.getLogger('commands')


def tag_volumes(client, system_tag, volume_tag):
    '''Tag all the volumes that must be duplicated in another Region.

    :param client: boto3 client
    :param system_tag str: value of the Tag used to mark system disks
    :param volume_tag str: value of the Tag used to mark a disk to be tagged
    '''

    # Find all instances (handle the native pagination) and build
    # a dict with InstanceId as key
    instance_ids = {}
    next_token = None
    while True:
        try:
            if next_token is None:
                instances_slice = client.describe_instances(MaxResults=MAX_RESULTS)
            else:
                instances_slice = client.describe_instances(MaxResults=MAX_RESULTS, NextToken=next_token)

            for resv in instances_slice['Reservations']:
                for instance in resv['Instances']:
                    instance_ids[instance['InstanceId']] = instance
        except Exception as e:
            raise Exception(f"Could not retrieve instances description {e}")

        if 'NextToken' in instances_slice:
            std_logger.info("MaxResults is too low for describe_instances, go on with next_token...")
            next_token = instances_slice['NextToken']
        else:
            break

    # Find all the volumes that must be snapshotted
    volumes = []
    next_token = None
    while True:
        try:
            if next_token is None:
                volumes_slice = client.describe_volumes(MaxResults=MAX_RESULTS, Filters=[{'Name': f'tag:{volume_tag}', 'Values': ['True']}])
            else:
                volumes_slice = client.describe_volumes(MaxResults=MAX_RESULTS, Filters=[{'Name': f'tag:{volume_tag}', 'Values': ['True']}], NextToken=next_token)

            volumes += volumes_slice['Volumes']
        except Exception as e:
            raise Exception(f"Could not retrieve volumes description {e}")

        if 'NextToken' in volumes_slice:
            std_logger.info("MaxResults is too low for describe_volumes, go on with next_token...")
            next_token = volumes_slice['NextToken']
        else:
            break

    for volume in volumes:
        # Add a tag with attachment info
        #print(volume)
        attachments = volume['Attachments']

        # TODO: handle only ONE attachment
        if len(attachments) > 1:
            std_logger.info(f"Volume {volume['VolumeId']} is multi-attached. Only the first attachment will be managed")

        if not len(attachments) or attachments[0]['State'] != 'attached':
            std_logger.info(f"Volume {volume['VolumeId']} is not attached")
            continue

        instance_id = attachments[0]['InstanceId']
        volume_id = volume['VolumeId']
        if instance_id not in instance_ids:
            raise Exception(f"No instance found for InstanceId {instance_id} referenced by volume {volume_id}")

        instance = instance_ids[instance_id]
        device = attachments[0]['Device']
        instance_name = _get_instance_from_id(volume_id, instance_id, instance)
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

                security_groups = _linearize(instance['SecurityGroups'])
                tags.append({'Key': 'SecurityGroups', 'Value': security_groups})
                break

        client.create_tags(Resources=[volume_id], Tags=tags)


def _get_instance_from_id(volume_id, instance_id, instance):
    for tag in instance['Tags']:
        if tag['Key'] == 'Name':
            return tag['Value']

    raise Exception(f"Instance {instance_id} has no Name tag !")


def _linearize(security_groups):
    sec = ""
    for security_goup in security_groups:
        sec = sec + security_goup['GroupName'] + ':' + security_goup['GroupId'] + ':'

    return sec


if __name__ == '__main__':
    # standalone & batch mode
    from optparse import OptionParser
    import boto3

    usage = "%prog [--region=REGION] [--system-tag=SYSDISK] [--volume-tag=MUSTSNAP]"

    parser = OptionParser(usage=usage, version="1.0")
    parser.add_option("-r", "--region", dest="region", help="Region where the EBS are located", default=None)
    parser.add_option("-s", "--system-tag", dest="system_tag", help="Name of the Tag put on System Disk", default="SYSDISK")
    parser.add_option("-v", "--volume-tag", dest="volume_tag", help="Name of the Tag put on an EBS that must ne snapshotted", default="MUSTSNAP")
    (opts,args) = parser.parse_args()

    client = boto3.client("ec2", region_name=opts.region)
    tag_volumes(client, opts.system_tag, opts.volume_tag)

