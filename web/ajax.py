import json
import boto3
import os
import logging
from datetime import datetime, timedelta
from operator import itemgetter
from .log import *
from django.http import HttpResponse, Http404
from django.contrib.auth.decorators import login_required
from .decorators import user_is_owner
from .models import Customer
from . import utils
from . import checks as ck

std_logger = logging.getLogger('general')


def get_customers(request):
    queryset = Customer.objects.all()
    names = []
    for q in queryset: names.append(q.name)
    return HttpResponse(json.dumps({'status': True, 'names': names}), content_type="application/json")


@login_required
@user_is_owner
def check_permission(request, cust_name, perm):
    '''Check if the given IAM permission is avaliable.

       Returns a tri-state value :
       True, False, 'unknown'
    '''
    customer = Customer.objects.get(name=cust_name)
    session = utils.get_session(customer)
    value = False

    try:
        value = True
        if perm == 'ec2_describe_addresses':
            client = utils.get_client(customer, 'ec2')
            ips = client.describe_addresses()
        elif perm == 'ec2_describe_reserved_instances':
            client = utils.get_client(customer, 'ec2')
            rsvd = client.describe_reserved_instances()
        elif perm == 'ec2_describe_instances':
            ec2 = list(session.resource('ec2').instances.all())
        elif perm == 'ec2_describe_volumes':
            volumes = list(session.resource('ec2').volumes.all())
        elif perm == 'ec2_describe_snapshots':
            client = utils.get_client(customer, 'ec2')
            response = client.describe_snapshots(OwnerIds=[customer.owner_id])
        elif perm == 'ec2_describe_images':
            ec2 = session.resource('ec2')
            amis = list(ec2.images.filter(Owners=['self']))
        elif perm == 'cw_get_metrics_statistics':
            volumes = list(session.resource('ec2').volumes.all())
            cloudwatch = utils.get_cloudwatch(customer)
            if volumes and len(volumes):
                dummy = ck.get_cw_volume_iops(cloudwatch, volumes[0].id, 2)
            else:
                value = 'unknown'
        elif perm == 'elb_describe_loadbalancers':
            client = utils.get_client(customer, 'elb')
            elbs = client.describe_load_balancers()
        elif perm == 'elb_describe_target_groups':
            client = utils.get_client(customer, 'elbv2')
            target_groups = client.describe_target_groups()
        elif perm == 'route53_list_hosted_zones':
            route53 = session.client('route53')
            zone_list = route53.list_hosted_zones(MaxItems='1')
        elif perm == 'route53_list_resources_record_sets':
            route53 = session.client('route53')
            zone_list = route53.list_hosted_zones(MaxItems='1')
            if zone_list and len(zone_list['HostedZones']):
                rr_set = route53.list_resource_record_sets(HostedZoneId=zone_list['HostedZones'][0]['Id'], MaxItems='1')
            else:
                value = 'unknown'
        elif perm == 'elasticache_describe_clusters':
            client = utils.get_elasticache(customer)
            caches = client.describe_cache_clusters()
        else:
            value = 'unkonwn'

    except Exception as e:
        value = False

    return HttpResponse(json.dumps({ 'value': value, 'perm': perm }), content_type='application/json')


@login_required
@user_is_owner
def get_instance_metrics(request, cust_name, instance_id):
    customer = Customer.objects.get(name=cust_name)
    cloudwatch = utils.get_cloudwatch(customer)

    now = datetime.utcnow()
    past = now - timedelta(minutes=30)
    future = now + timedelta(minutes=10)

    results = cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='CPUUtilization',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=past,
                EndTime=future,
                Period=300,
                Statistics=['Average']
    )
    datapoints = results['Datapoints']
    if datapoints and len(datapoints):
        last_datapoint = sorted(datapoints, key=itemgetter('Timestamp'))[-1]
        utilization = last_datapoint['Average']
        load = round((utilization / 100.0), 2)
        timestamp = str(last_datapoint['Timestamp'])
    else:
        load = 'N/A'

    return HttpResponse(json.dumps({ 'cpu': load }), content_type='application/json')


@login_required
@user_is_owner
def get_elb_reqcount(request, cust_name, elb_type, elb_name):
    customer = Customer.objects.get(name=cust_name)
    cloudwatch = utils.get_cloudwatch(customer)

    now = datetime.utcnow()
    past = now - timedelta(days=2)

    #print(elb_type, elb_name)
    if elb_type != 'classic':
        elb_name = elb_name[elb_name.index('/')+1:]

    #print(elb_type, elb_name)
    try:
        results = cloudwatch.get_metric_statistics(
            Namespace='AWS/ELB' if elb_type == 'classic' else 'AWS/ApplicationELB',
            MetricName='RequestCount',
            Dimensions=[{'Name': 'LoadBalancerName' if elb_type == 'classic' else 'LoadBalancer', 'Value': elb_name}],
            StartTime=past,
            EndTime=now - timedelta(days=1),
            Period=86400,
            Statistics=['Sum']
        )

        datapoints = results['Datapoints']
        if datapoints and len(datapoints):
            req_count = datapoints[0]['Sum']
        else:
            req_count = 'N/A'
    except Exception as e:
        req_count = 'Err'
        #print(e)

    #print('ELB Type:', elb_type, 'ELB Name:', elb_name, '#req:', req_count)

    return HttpResponse(json.dumps({ 'req_count': req_count }), content_type='application/json')


@login_required
@user_is_owner
def get_cache_metrics(request, cust_name, cache_type, cache_name):
    customer = Customer.objects.get(name=cust_name)
    cloudwatch = utils.get_cloudwatch(customer)

    now = datetime.utcnow()
    past = now - timedelta(days=2)

    #print(cache_type, cache_name)
    try:
        results = cloudwatch.get_metric_statistics(
            Namespace='AWS/ElastiCache',
            MetricName='CPUUtilization',
            Dimensions=[{'Name': 'CacheClusterId', 'Value': cache_name}],
            StartTime=past,
            EndTime=now - timedelta(days=1),
            Period=86400,
            Statistics=['Average', 'Maximum']
        )
        #print(results)
        datapoints = results['Datapoints']
        if datapoints and len(datapoints):
            cpu_max = datapoints[0]['Maximum']
            cpu_avg = datapoints[0]['Average']
        else:
            cpu_max = cpu_avg = 'N/A'
    except Exception as e:
        cpu_max = cpu_avg = 'Err'
        #print(e)

    try:
        if cache_type == 'redis':
            results = cloudwatch.get_metric_statistics(
                Namespace='AWS/ElastiCache',
                MetricName='GetTypeCmds',
                Dimensions=[{'Name': 'CacheClusterId', 'Value': cache_name}],
                StartTime=past,
                EndTime=now - timedelta(days=1),
                Period=86400,
                Statistics=['Sum']
            )
        else:
            results = cloudwatch.get_metric_statistics(
                Namespace='AWS/ElastiCache',
                MetricName='CmdGet',
                Dimensions=[{'Name': 'CacheClusterId', 'Value': cache_name}],
                StartTime=past,
                EndTime=now - timedelta(days=1),
                Period=86400,
                Statistics=['Sum']
            )

        print(results)
        datapoints = results['Datapoints']
        if datapoints and len(datapoints):
            total_gets = datapoints[0]['Sum']
        else:
            total_gets = 'N/A'
    except Exception as e:
        total_gets = 'Err'
        #print(e)

    return HttpResponse(json.dumps({ 'cpu_max': int(cpu_max), 'cpu_avg': int(cpu_avg), 'total_gets': total_gets }), content_type='application/json')


@login_required
@user_is_owner
def get_vol_ops(request, cust_name, volume_id):
    try:
        customer = Customer.objects.get(name=cust_name)
        cloudwatch = utils.get_cloudwatch(customer)
        read_ops, write_ops = ck.get_cw_volume_iops(cloudwatch, volume_id, 30)
    except Exception as e:
        std_logger.error("get_vol_ops failed for Customer " + cust_name)
        read_ops = write_ops = 'Err'

    return HttpResponse(json.dumps({ 'read_ops': read_ops, 'write_ops': write_ops }), content_type='application/json')


@login_required
@user_is_owner
def get_s3_metrics(request, cust_name, bucket_name, location):
    customer = Customer.objects.get(name=cust_name)
    if customer.region != location:
        customer.region = location
        cloudwatch = utils.get_cloudwatch(customer)
    else:
        cloudwatch = utils.get_cloudwatch(customer)

    now = datetime.utcnow()
    past = now - timedelta(minutes=30)
    future = now + timedelta(minutes=10)

    results = cloudwatch.get_metric_statistics(
        Namespace='AWS/S3',
        MetricName='BucketSizeBytes',  # 'NumberOfObjects' => AllStorageTypes
        Dimensions=[
            {'Name': 'BucketName', 'Value': bucket_name},
            {'Name': 'StorageType', 'Value': 'StandardStorage'}  # StandardIAStorage,  ReducedRedundancyStorage
        ],
        StartTime=now - timedelta(days=2),
        EndTime=now,
        Period=86400,
        Statistics=['Average']
    )

    if len(results["Datapoints"]):
        size = results["Datapoints"][0]["Average"]
        size //= 1024 * 1024 * 1024;  # GiB conversion
    else:
        size = 'n/a'

    results = cloudwatch.get_metric_statistics(
        Namespace='AWS/S3',
        MetricName='NumberOfObjects',
        Dimensions=[
            {'Name': 'BucketName', 'Value': bucket_name},
            {'Name': 'StorageType', 'Value': 'AllStorageTypes'}
        ],
        StartTime=now - timedelta(days=2),
        EndTime=now,
        Period=86400,
        Statistics=['Average']
    )

    nb_obj = results["Datapoints"][0]["Average"] if len(results["Datapoints"]) else 'n/a'

    return HttpResponse(json.dumps({ 'bucket_size': size, 'nb_objects': nb_obj }), content_type='application/json')

