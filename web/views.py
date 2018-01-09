# import json
# import boto3
from django.utils.translation import ugettext as _
from django.shortcuts import render, redirect
from django.http import HttpResponse
from . import utils
from .models import Customer
from . import pricing

# access_id = 'abc'
# secret_id = 'xyz'


def index(request):
    names = _get_customers()
    context = { 'names': names }
    return render(request, 'index.html', context)


def goto_console(request, cust_name):
    customer = _get_customer(cust_name)
    return redirect(customer.console_url)


def get_instances(request, cust_name):
    names = _get_customers()
    customer = _get_customer(cust_name)
    client = utils.get_client(customer, 'ec2')
    session = utils.get_session(customer)

    ec2list = []
    ec2 = session.resource('ec2')
    ips = client.describe_addresses()
    #print(ips)

    running = 0
    price = 0
    for inst in ec2.instances.all():
        if inst.state['Name'] == 'running': running += 1

        # Extract the 'name' from tags
        name = ''
        if inst.tags:
            for tag in inst.tags:
                if tag['Key'] == 'Name':
                    name = tag['Value']
                    break

        ec2list.append({'instance_id': inst.id,
                        'instance_type': inst.instance_type,
                        'instance_state': inst.state,
                        'public_ip': inst.public_ip_address,
                        'is_elastic': _is_elastic_ip(ips, inst.public_ip_address),
                        'private_ip': inst.private_ip_address,
                        'zone' : inst.placement['AvailabilityZone'],
                        'tags': inst.tags,
                        'name': name})

        if inst.instance_type in pricing.ec2_pricing and inst.state['Name'] == 'running':
            price += pricing.ec2_pricing[inst.instance_type]

    return render(request, 'instances.html', { 'current': cust_name, 'names': names, 'ec2list': ec2list, 'running_count': running, 'price': int(price * 24 * 30) })


def get_snapshots(request, cust_name):
    names = _get_customers()
    customer = _get_customer(cust_name)
    client = utils.get_client(customer, 'ec2')
    response = client.describe_snapshots(OwnerIds=[customer.owner_id])
    snapshot_list = response['Snapshots']

    snaplist = []
    for snap in snapshot_list:
        snaplist.append(snap)
        '''
        snaplist.append({'snapshot_id': snap.SnapshotId,
                         'volume_id': snap.VolumeId,
                         'start_time': snap.StartTime,
                         'state': snap.State,
                         'volume_size': snap.VolumeSize,
                         'description': snap.Description})
        '''
    return render(request, 'snapshots.html', { 'current': cust_name, 'names': names, 'snaplist': snaplist })


def check_snapshots(request, cust_name):
    names = _get_customers()
    customer = _get_customer(cust_name)
    session = utils.get_session(customer)
    ec2 = session.resource('ec2')
    client = utils.get_client(customer, 'ec2')
    response = client.describe_snapshots(OwnerIds=[customer.owner_id])
    snapshot_list= response['Snapshots']

    # Algo : loop on EC2 instances to get the Volumes ID
    #           loop on the Snapshots to check if the Volume ID match
    # Must determine if an EC2 instance is snapshoted or no, fully or partially
    # also get the date of last snapshot
    ec2list = []
    ec2vol = {}
    for inst in ec2.instances.all():
        ec2vol[inst.id] = { 'all': [] }
        name = ''
        for tag in inst.tags:
            if tag['Key'] == 'Name':
                name = tag['Value']
                break

        volumes = inst.volumes.all()
        volume_snapped = volume_count = 0
        start_time = ''
        for vol in volumes:
            volume_count += 1
            if not vol.volume_id in ec2vol[inst.id]:
                ec2vol[inst.id][vol.volume_id] = []
            for snap in snapshot_list:
                if vol.volume_id == snap['VolumeId']:
                    volume_snapped += 1
                    start_time = snap['StartTime']
                    ec2vol[inst.id][vol.volume_id].append(start_time)
                    ec2vol[inst.id]['all'].append(start_time)
                    break

        ec2list.append({'instance_id': inst.id,
                        'instance_state': inst.state,
                        'name': name,
                        'volume_count': volume_count,
                        'volume_snapped': volume_snapped,
                        'start_time': max(ec2vol[inst.id]['all']) if len(ec2vol[inst.id]['all']) else '',  # should be per volume
                        })

    return render(request, 'check_snapshots.html', { 'current': cust_name, 'names': names, 'ec2list': ec2list })


def _get_customers():
    queryset = Customer.objects.all()
    names = []
    for q in queryset: names.append(q.name)
    return sorted(names)


def _get_customer(cust_name):
    customer = Customer.objects.get(name=cust_name)
    return customer

def _is_elastic_ip(ips, public_ip):
    if not 'Addresses' in ips: return False
    for ip in ips['Addresses']:
        if 'PublicIp' in ip and ip['PublicIp'] == public_ip: return True
    return False



