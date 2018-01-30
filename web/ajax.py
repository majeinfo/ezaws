import json
import boto3
import os
from datetime import datetime, timedelta
from operator import itemgetter
from .log import *
from django.http import HttpResponse, Http404
from django.contrib.auth.decorators import login_required
from .decorators import user_is_owner
from .models import Customer
from . import utils


def get_customers(request):
    queryset = Customer.objects.all()
    names = []
    for q in queryset: names.append(q.name)
    return HttpResponse(json.dumps({'status': True, 'names': names}), content_type="application/json")


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
        #print(results)
        datapoints = results['Datapoints']
        if datapoints and len(datapoints):
            req_count = datapoints[0]['Sum']
        else:
            req_count = 'N/A'
    except Exception as e:
        req_count = 'Err'
        #print(e)

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