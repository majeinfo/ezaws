import multiprocessing as mp
from operator import itemgetter
from django.utils import timezone
import collections
import logging
from datetime import datetime, timedelta
from . import utils
from . import log
import aws.params as params
import aws.pricing as pricing
import aws.definitions as awsdef

std_logger = logging.getLogger('general')


def check_orphan_volumes(customer, volumes):
    log.log_time('-> check_orphan_volumes')
    costs = pricing.Pricing(customer.region)
    total_size = 0
    total_price = 0
    orphans = []
    vol_sizes = {}
    for vol in volumes:
        #print(vol.attachments)
        if not len(vol.attachments):
            orphans.append(vol.id)
            total_size += vol.size
            total_price += costs.get_EBS_cost_per_month(vol.size, vol.volume_type, vol.iops)
            vol_sizes[vol.id] = vol.size

    log.log_time('<- check_orphan_volumes')
    return { 'orphans': orphans, 'total_size': total_size, 'vol_sizes': vol_sizes, 'total_price': total_price }


def check_orphan_amis(customer, amis, instances):
    log.log_time('-> check_orphan_amis')
    costs = pricing.Pricing(customer.region)
    orphans = {}
    devices = {}
    total_price = 0
    total_size = 0  # in GiB
    ami_attrs = {}
    ami_names = {}

    for ami in amis:
        #print(ami.id)
        orphans[ami.id] = True
        devices[ami.id] = ami.block_device_mappings
        ami_names[ami.id] = utils.get_ami_name(ami, customer.aws_resource_tag_name)

    for inst in instances:
        if inst.image_id in orphans:
            del orphans[inst.image_id]

    # Compute the size per AMI and the total size
    ami_sizes = collections.defaultdict(int)
    for ami_id in orphans.keys():
        #print(ami_id)
        for vol in devices[ami_id]:
            #print(vol)
            if 'Ebs' not in vol:
                continue
            vol_size = vol['Ebs']['VolumeSize']
            ami_attrs[ami_id] = {'name': ami_names[ami_id]}
            ami_sizes[ami_id] += vol_size
            total_size += vol_size
            total_price += costs.get_EBS_cost_per_month(vol_size, 'snapshot', 0)

        ami_attrs[ami_id]['size'] = ami_sizes[ami_id]

    log.log_time('<- check_orphan_amis')
    return { 'orphans': orphans.keys(), 'total_size': total_size, 'ami_sizes': dict(ami_sizes),
             'total_price': total_price, 'ami_attrs': ami_attrs }


def check_orphan_eips(customer, eips):
    log.log_time('-> check_orphan_eips')
    costs = pricing.Pricing(customer.region)
    orphans = []
    total_price = 0

    for eip in eips:
        if ('InstanceId' not in eip) or (not eip['InstanceId']):
            orphans.append(eip['PublicIp'])
            total_price += costs.get_EIP_cost_per_month()

    log.log_time('<- check_orphan_eips')
    return { 'orphans': orphans, 'total_price': total_price }


def check_orphan_target_groups(customer, target_groups):
    log.log_time('-> check_orphan_target_groups')

    orphans = []

    for group in target_groups['TargetGroups']:
        if not len(group['LoadBalancerArns']):
            orphans.append(group['TargetGroupName'])

    log.log_time('<- check_orphan_target_groups')
    return { 'orphans': orphans }


def check_stopped_instances(customer, instances, volumes):
    log.log_time('-> check_stopped_instances')
    costs = pricing.Pricing(customer.region)
    stopped_inst = {}
    total_size = 0
    total_price = 0
    for inst in instances:
        if inst.state['Code'] == 80: # 08 = 'stopped'
            # Compute the Volumes size
            total_vol_size, price = utils.get_ec2_volume_size_price(customer, inst.instance_id, volumes)
            total_price += price

            # for vol in volumes:
            #     if len(vol.attachments) and vol.attachments[0]['InstanceId'] == inst.instance_id:
            #         total_vol_size += vol.size
            #         total_price += costs.get_EBS_cost_per_month(vol.size, vol.volume_type, vol.iops)
            #         #break

            name = utils.get_instance_name(inst, customer.aws_resource_tag_name)
            stopped_inst[inst.instance_id] = { 'total_vol_size': total_vol_size, 'name': name }
            total_size += total_vol_size

    log.log_time('<- check_stopped_instances')
    return { 'stopped_inst': stopped_inst, 'total_size': total_size, 'total_price': total_price }


def check_long_time_stopped_instances(customer, instances):
    log.log_time('-> check_long_time_stopped_instances')
    stopped_inst = {}
    for inst in instances:
        if inst.state['Name'] == 'stopped':
            #print(inst.launch_time)
            now = timezone.now()
            past = now - timedelta(days=params.parm_unused_instances_nu_days)
            print(past)
            if inst.launch_time < past:
                name = utils.get_instance_name(inst, customer.aws_resource_tag_name)
                stopped_inst[inst.instance_id] = { 'days': (now - inst.launch_time).days, 'name': name }

    log.log_time('<- check_long_time_stopped_instances')
    return { 'long_time_stopped_inst': stopped_inst }


def check_underused_volume(customer, volumes, instances):
    log.log_time('-> check_underused_volume')
    costs = pricing.Pricing(customer.region)
    cloudwatch = utils.get_cloudwatch(customer)
    nu_days = params.parm_unused_volumes_nu_days
    underused_volumes = {}
    underused_size = 0
    underused_price = 0
    for vol in volumes:
        read_ops, write_ops = get_cw_volume_iops(cloudwatch, vol.id, nu_days)
        if (read_ops is not None) and (write_ops is not None) and \
                (read_ops < params.parm_unused_volumes_min_read_ops * nu_days) and \
                (write_ops < params.parm_unused_volumes_min_write_ops * nu_days):
            underused_volumes[vol.id] = {}
            underused_size += vol.size
            underused_price += costs.get_EBS_cost_per_month(vol.size, vol.volume_type, vol.iops)

            if (not len(vol.attachments)) or ('InstanceId' not in vol.attachments[0]):
                continue

            inst_id = vol.attachments[0]['InstanceId']
            for inst in instances:
                if inst_id == inst.instance_id:
                    inst_name = utils.get_instance_name(inst, customer.aws_resource_tag_name)
                    if inst_name is None:
                        inst_name = inst.instance_id
                    break
            underused_volumes[vol.id]['inst_name'] = inst_name
            underused_volumes[vol.id]['vol_size'] = vol.size
            underused_volumes[vol.id]['device'] = vol.attachments[0]['Device']

    log.log_time('<- check_underused_volume')
    return { 'underused_volumes': underused_volumes, 'underused_size': underused_size, 'underused_price' : underused_price }


def get_cw_volume_iops(cw, volume_id, nu_days):
    '''Return (read_ops, write_ops) for the last nu_days.
       May generate an exception (for ex: access denied in CW)
    '''
    log.log_time('-> get_cw_volume_iops')
    now = datetime.utcnow()
    past = now - timedelta(days=nu_days)
    #future = now + timedelta(minutes=10)

    try:
        results = cw.get_metric_statistics(
            Namespace='AWS/EBS',
            MetricName='VolumeReadOps',
            Dimensions=[{'Name': 'VolumeId', 'Value': volume_id}],
            StartTime=past,
            EndTime=now - timedelta(days=1),
            Period=86400 * nu_days,
            Statistics=['Sum']
        )
        #print(results)
        datapoints = results['Datapoints']
        if datapoints and len(datapoints):
            read_ops = int(datapoints[0]['Sum'])
        else:
            read_ops = None
    except Exception as e:
        std_logger.error("get_cw_volume_ops read_ops error: " % (e,))
        read_ops = None
        raise e

    try:
        results = cw.get_metric_statistics(
            Namespace='AWS/EBS',
            MetricName='VolumeWriteOps',
            Dimensions=[{'Name': 'VolumeId', 'Value': volume_id}],
            StartTime=past,
            EndTime=now - timedelta(days=1),
            Period=86400 * nu_days,
            Statistics=['Sum']
        )
        #print(results)
        datapoints = results['Datapoints']
        if datapoints and len(datapoints):
            write_ops = int(datapoints[0]['Sum'])
        else:
            write_ops = None
    except Exception as e:
        std_logger.error("get_cw_volume_ops write_ops error: " % (e,))
        write_ops = None
        raise e

    log.log_time('<- get_cw_volume_iops')
    return read_ops, write_ops


# RI which scope is AZ can be used for Instances in same AZ,
#   The attributes (tenancy, platform, Availability Zone, instance type, and instance size) must match
# RI which scope is Region can be used for Instances in any AZ of the Region
#   If the platform is Linux (no RHEL/SLES) the attributes (tenancy, platform, type) must match and the
#   size normalization applies
#   else all the attributes must match except the AZ
#
# Returns allocation :
# {
#   <ri_instance_id> : {
#       'max_instance_count': <value>,
#       'normalized_size': <value>,
#       'remaining_size': <value>,
#       'ec2_instances': [
#           { 'ec2_id': <ec2_instance_id>, 'type': <value>, 'size': <value>, 'percent': <value>, 'name': <value>  },...
#       ], ...
#   },....
# }
def check_reserved_instances(customer, rsvlist, ec2list):
    log.log_time('-> check_reserved_instances')
    rsv_alloc = {}
    unused_ec2 = {}     # unused_ec2[inst_id] = { 'inst': <instance>, 'name': <name>, 'value': <percentage_of_unused>, 'days': <value in days> }

    # Init rsv_alloc:
    for rsv in rsvlist:
        rsv_id = rsv['ReservedInstancesId']
        rsv_count = rsv['InstanceCount']
        rsv_type = rsv['InstanceType']
        rsv_norm_size = awsdef.instance_normalization[rsv_type.split('.')[1]]
        rsv_alloc[rsv_id] = {'max_instance_count': rsv_count, 'normalized_size': rsv_norm_size * rsv_count,
                             'ec2_instances': [], 'remaining_size': rsv_norm_size * rsv_count}

    # Init unused_ec2
    now = timezone.now()
    for ec2 in ec2list:
        if not utils.instance_is_running(ec2):
            continue
        ec2_type = ec2.instance_type
        unused_ec2[ec2.id] = {'inst': ec2, 'name': utils.get_instance_name(ec2, customer.aws_resource_tag_name),
                              'value': awsdef.instance_normalization[ec2_type.split('.')[1]],
                              'days': (now - ec2.launch_time).days}

    # Look for matching EC2 for RI which scope is AZ
    for rsv in rsvlist:
        if rsv['Scope'] == 'Region':
            continue
        rsv_id = rsv['ReservedInstancesId']
        rsv_az = rsv['AvailabilityZone']
        rsv_count = rsv['InstanceCount']
        rsv_type = rsv['InstanceType']
        rsv_pf = rsv['ProductDescription']
        rsv_ten = rsv['InstanceTenancy']

        for ec2 in ec2list:
            # EC2 already allocated and running
            if ec2.id not in unused_ec2 or not utils.instance_is_running(ec2):
                continue

            ec2_az = ec2.placement['AvailabilityZone']
            ec2_ten = ec2.placement['Tenancy'] if 'Tenancy' in ec2.placement else None
            ec2_pf = ec2.platform
            ec2_type = ec2.instance_type

            if rsv_az == ec2_az and rsv_type == ec2_type and rsv_ten == ec2_ten and rsv_pf == ec2_pf:
                if rsv_count > len(rsv_alloc[rsv_id]['ec2_instances']):
                    rsv_alloc[rsv_id]['ec2_instances'].append({'ec2_id': ec2.id, 'size': 1, 'type': ec2_type,
                                                               'percent': 100,
                                                               'name': utils.get_instance_name(ec2, customer.aws_resource_tag_name)})
                    del unused_ec2[ec2.id]

    # Look for matching EC2 with RI which scope is Region but without Flexibility
    for rsv in rsvlist:
        if rsv['Scope'] != 'Region':
            continue
        rsv_id = rsv['ReservedInstancesId']
        rsv_count = rsv['InstanceCount']
        rsv_type = rsv['InstanceType']
        rsv_pf = rsv['ProductDescription']
        rsv_ten = rsv['InstanceTenancy']

        if rsv_ten == 'default' and rsv_pf.startswith('Linux/UNIX'):
            continue

        for ec2 in ec2list:
            # EC2 already allocated and running
            if ec2.id not in unused_ec2 or not utils.instance_is_running(ec2):
                continue

            ec2_ten = ec2.placement['Tenancy'] if 'Tenancy' in ec2.placement else None
            ec2_pf = ec2.platform
            ec2_type = ec2.instance_type

            if rsv_type == ec2_type and rsv_ten == ec2_ten and rsv_pf == ec2_pf:
                if rsv_count > len(rsv_alloc[rsv_id]['ec2_instances']):
                    rsv_alloc[rsv_id].append({'ec2_id': ec2.id, 'size': 1, 'percent': 100, 'type': ec2_type,
                                              'name': utils.get_instance_name(ec2, customer.aws_resource_tag_name)})
                    del unused_ec2[ec2.id]

    # Look for matching EC2 with RI which scope is Region with Flexibility
    for rsv in rsvlist:
        if rsv['Scope'] != 'Region':
            continue
        rsv_id = rsv['ReservedInstancesId']
        rsv_type = rsv['InstanceType']
        rsv_pf = rsv['ProductDescription']
        rsv_ten = rsv['InstanceTenancy']

        if rsv_ten != 'default' or not rsv_pf.startswith('Linux/UNIX'):
            continue

        # For each RI we try to find the "highest" EC2 instance that can fit and if an instance fit
        # we must loop to find another one
        while True:
            best_ec2 = None
            best_size = 0.0
            for ec2 in ec2list:
                # EC2 already allocated and running
                if ec2.id not in unused_ec2 or not utils.instance_is_running(ec2):
                    continue

                ec2_ten = ec2.placement['Tenancy'] if 'Tenancy' in ec2.placement else None
                ec2_pf = ec2.platform
                ec2_type = ec2.instance_type
                if rsv_ten != ec2_ten or rsv_pf == ec2_pf:
                    continue

                # Flexibility applies
                # instance type must match (t2, m3,...)
                if rsv_type.split('.')[0] != ec2_type.split('.')[0]:
                    continue
                ec2_size = awsdef.instance_normalization[ec2_type.split('.')[1]]
                if ec2_size <= rsv_alloc[rsv_id]['remaining_size']:
                    if ec2_size > best_size:
                        best_size = ec2_size
                        best_ec2 = ec2

            if best_ec2:
                rsv_alloc[rsv_id]['ec2_instances'].append({'ec2_id': best_ec2.id, 'size': best_size, 'type': best_ec2.instance_type,
                                                           'percent': 100, 'name': utils.get_instance_name(best_ec2, customer.aws_resource_tag_name)})
                rsv_alloc[rsv_id]['remaining_size'] -= best_size
                del unused_ec2[best_ec2.id]
            else:
                break

    # TODO: try to affect unused_ec2 instances to partially allocated RI

    #print(rsv_alloc)
    #print(unused_ec2)

    log.log_time('<- check_reserved_instances')
    return rsv_alloc, unused_ec2


# if boto3 were asyncio compatible, this would be unuseful, but
# we need to improve performance with parallelism
cloudwatch = None
def check_instances_usage(customer, instances):
    log.log_time('-> check_instances_usage')
    global  cloudwatch
    cloudwatch = utils.get_cloudwatch(customer)
    buckets = {}
    inst_list = []
    inst_name = {}

    for inst in instances:
        if inst.state['Name'] != awsdef.EC2_RUNNING:
            continue

        inst_list.append(inst.id)
        inst_name[inst.id] = utils.get_instance_name(inst, customer.aws_resource_tag_name)

    # for inst in instances:
    #     if inst.state['Name'] == awsdef.EC2_RUNNING:
    #         cpu, netin, netout = check_instance_usage(cloudwatch, inst)
    #         if cpu is None or netin is None or netout is None:
    #             continue
    #         bucket = {
    #             'name': utils.get_instance_name(inst, customer.aws_resource_tag_name),
    #             'weekdays': [],
    #             'hours': [],
    #         }
    #         for a, b, c in zip(cpu['weekdays'], netin['weekdays'], netout['weekdays']):
    #             bucket['weekdays'].append(a + b + c)
    #
    #         for a, b, c in zip(cpu['hours'], netin['hours'], netout['hours']):
    #             bucket['hours'].append(a + b + c)
    #
    #         buckets[inst.id] = bucket
    #
    # return buckets

    with mp.Pool(processes=params.parm_parallelism_level) as pool:
        results = pool.map(_check_instance_usage, inst_list)

    #print(results)
    for inst, bucket in zip(inst_list, results):
        bucket['name'] = inst_name[inst]
        buckets[inst] = bucket

    log.log_time('<- check_instances_usage')
    return buckets


def _check_instance_usage(inst_id):
    log.log_time('-> _check_instances_usage: %s' % inst_id)
    cpu, netin, netout = check_instance_usage(cloudwatch, inst_id)
    if cpu is None or netin is None or netout is None:
        return None

    bucket = {
        #'name': utils.get_instance_name(inst, customer.aws_resource_tag_name),
        'name': inst_id,
        'weekdays': [],
        'hours': [],
    }
    for a, b, c in zip(cpu['weekdays'], netin['weekdays'], netout['weekdays']):
        bucket['weekdays'].append(a + b + c)

    for a, b, c in zip(cpu['hours'], netin['hours'], netout['hours']):
        bucket['hours'].append(a + b + c)

    log.log_time('<- _check_instances_usage: %s' % inst_id)
    return bucket


def check_instance_usage(cw, inst_id):
    now = datetime.utcnow()
    now = datetime(now.year, now.month, now.day, now.hour)
    past = now - timedelta(minutes=60*24*30)
    future = now + timedelta(minutes=60)

    results = cw.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='CPUUtilization',
                Dimensions=[{'Name': 'InstanceId', 'Value': inst_id}],
                StartTime=past,
                EndTime=future,
                Period=60*60,   # in seconds
                Statistics=['Average']
    )
    cpu_buckets = _put_in_buckets(results, 5)

    '''
    Disk Read/Write must apply on EBS
    results = cw.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='DiskReadBytes',
                Dimensions=[{'Name': 'InstanceId', 'Value': inst_id}],
                StartTime=past,
                EndTime=future,
                Period=60*60,   # in seconds
                Statistics=['Average']
    )
    readbytes_buckets = _put_in_buckets(results, 10)

    results = cw.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='DiskWriteBytes',
                Dimensions=[{'Name': 'InstanceId', 'Value': inst_id}],
                StartTime=past,
                EndTime=future,
                Period=60*60,   # in seconds
                Statistics=['Average']
    )
    writebytes_buckets = _put_in_buckets(results, 10)
    '''

    results = cw.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='NetworkIn',
                Dimensions=[{'Name': 'InstanceId', 'Value': inst_id}],
                StartTime=past,
                EndTime=future,
                Period=60*60,   # in seconds
                Statistics=['Average']
    )
    netin_buckets = _put_in_buckets(results, 100000)

    results = cw.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='NetworkOut',
                Dimensions=[{'Name': 'InstanceId', 'Value': inst_id}],
                StartTime=past,
                EndTime=future,
                Period=60*60,   # in seconds
                Statistics=['Average']
    )
    netout_buckets = _put_in_buckets(results, 100000)

    return cpu_buckets, netin_buckets, netout_buckets


def _put_in_buckets(results, threshold):
    datapoints = results['Datapoints']
    if not datapoints or not len(datapoints):
        return None

    datapoints = sorted(datapoints, key=itemgetter('Timestamp'))

    buckets = {
        'weekdays' : [ 0 ] * 7,  # 0=monday
        'hours': [ 0 ] * 24,
    }

    for point in datapoints:
        avg = point['Average']
        if avg > threshold:
            t = point['Timestamp']
            wd = t.weekday()
            buckets['weekdays'][wd] += 1
            buckets['hours'][t.hour] += 1

    return buckets


