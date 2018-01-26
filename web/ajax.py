import json
import boto3
from datetime import datetime, timedelta
from operator import itemgetter
from .log import *
from django.http import HttpResponse, Http404
from .models import Customer
from . import utils


def get_customers(request):
    queryset = Customer.objects.all()
    names = []
    for q in queryset: names.append(q.name)
    return HttpResponse(json.dumps({'status': True, 'names': names}), content_type="application/json")


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
