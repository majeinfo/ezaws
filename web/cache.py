import boto3
from django.contrib import messages
from . import utils

zone_rsets = None
volumes = None

def get_domains(request, customer):
    global zone_rsets
    if zone_rsets is not None:
        return zone_rsets

    zone_rsets = {}

    session = utils.get_session(customer)
    route53 = session.client('route53')
    maxItems = '200'  # TODO: set parameter

    while True:
        try:
            zone_list = route53.list_hosted_zones(MaxItems=maxItems)
        except Exception as e:
            if request:
                messages.error(request, e)
            return zone_rsets

        if zone_list['IsTruncated'] == True:
            maxItems = str(int(maxItems) * 2)
        else:
            zone_list = zone_list['HostedZones']
            break

    maxItems = '1000'  # TODO: set parameter

    try:
        for zone in zone_list:
            zone_rsets[zone['Name']] = []
            paginator = route53.get_paginator('list_resource_record_sets')
            page_iterator = paginator.paginate(HostedZoneId=zone['Id'], MaxItems=maxItems)
            for page in page_iterator:
                zone_rsets[zone['Name']] += page['ResourceRecordSets']

            #rsets = route53.list_resource_record_sets(HostedZoneId=zone['Id'], MaxItems=maxItems)
            # if rsets['IsTruncated'] == True:
            #     zone_rsets[zone['Name']] = rsets['ResourceRecordSets']
            #     print(zone, "truncated")

            #print(rsets)
            #zone_rsets[zone['Name']] = rsets['ResourceRecordSets']

            # print(zone_rsets['Name'])
            # rsets = rsets['ResourceRecordSets']
            # for rset in rsets:
            #     print('RRSet:', rset['Name'], rset['Type'])
            #     if 'ResourceRecords' in rset:
            #         for rr in rset['ResourceRecords']:
            #             print('RR:', rr['Value'])
            #     if 'AliasTarget' in rset:
            #         print('AliasTarget:', rset['AliasTarget']['DNSName'])

    except Exception as e:
        if request:
            messages.error(request, e)

    return zone_rsets


# TODO: need for a Paginator ?
def get_volumes(request, customer):
    global volumes
    if volumes:
        return volumes

    session = utils.get_session(customer)
    ec2 = session.resource('ec2')

    try:
        volumes = list(ec2.volumes.all())
    except Exception as e:
        if request:
            messages.error(request, e)
        return None

    return volumes



