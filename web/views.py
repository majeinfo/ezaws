# import json
# import boto3
import collections
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

        name = _get_instance_name(inst) or ''

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

    return render(request, 'instances.html', { 'current': cust_name, 'names': names, 'ec2list': ec2list, 'running_count': running, 'price': int(price * 24 * 31) })


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
        name = _get_instance_name(inst) or ''

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


# TODO: implémenter une alerte en fonction du RequestCount remonté par le CloudWatch : si nul, ELB à supprimer ?
def get_elbs(request, cust_name):
    names = _get_customers()
    customer = _get_customer(cust_name)
    client = utils.get_client(customer, 'elb')
    elbs = client.describe_load_balancers()
    session = utils.get_session(customer)
    ec2 = session.resource('ec2')   # to get the instance Name fro minstance ID
    inst_name_cache = _get_instances_name_cache(ec2)

    elblist = []
    price = 0

    # Classic ELB
    for elb in elbs['LoadBalancerDescriptions']:
        listeners = []
        for listener in elb['ListenerDescriptions']:
            listeners.append(listener['Listener']['LoadBalancerPort'])
        instances = []
        for inst in elb['Instances']:
            instances.append(inst_name_cache[inst['InstanceId']])

        elblist.append({
            'name': elb['LoadBalancerName'],
            'type': 'classic',
            'DNSName': elb['DNSName'],
            'listeners': listeners,
            'instances': instances,
            'target_groups': [],
        })
        price += pricing.elb_pricing['classic']['by_hour']

    # Applicative ELB
    client = utils.get_client(customer, 'elbv2')
    elbs = client.describe_load_balancers()
    target_groups = client.describe_target_groups()
    target_health = {}

    for elb in elbs['LoadBalancers']:
        e = {
            'name': elb['LoadBalancerName'],
            'type': elb['Type'],
            'DNSName': elb['DNSName'],
            'listeners': [],
            'instances': [],
            'target_groups': [],
        }

        for tgt in target_groups['TargetGroups']:
            for arn in tgt['LoadBalancerArns']:
                if elb['LoadBalancerArn'] == arn:
                    tgt_name = tgt['TargetGroupName']
                    e['target_groups'].append(tgt_name)
                    e['listeners'].append(tgt['Port'])

                    tgt_arn = tgt['TargetGroupArn']
                    if tgt_arn not in target_health:
                        health = client.describe_target_health(TargetGroupArn=tgt_arn)
                        target_health[tgt_name] = []
                        for h in health['TargetHealthDescriptions']:
                            target_health[tgt_name].append(h['Target']['Id'])

        for tgt in e['target_groups']:
            for inst in target_health[tgt]:
                name = inst_name_cache[inst]
                if name not in e['instances']:
                    e['instances'].append(name)

        e['instances']= sorted(e['instances'])
        elblist.append(e)

        price += pricing.elb_pricing['application']['by_hour']

    return render(request, 'elbs.html', {'current': cust_name, 'names': names, 'elblist': elblist, 'price': int(price * 24 * 31)})


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


def _get_instances_name_cache(ec2):
    '''Returns a dict with inst_id as a key and instance Name as value'''
    cache = collections.defaultdict(str)
    for inst in ec2.instances.all():
        cache[inst.instance_id] = _get_instance_name(inst) or inst.instance_id

    return cache


def _get_instance_name_from_id(ec2, inst_id):
    for inst in ec2.instances.all():
        if inst.instance_id == inst_id:
            return _get_instance_name(inst)

    return None


def _get_instance_name(inst):
    # Extract the 'name' from tags
    if inst.tags:
         for tag in inst.tags:
              if tag['Key'] == 'Name':
                   return tag['Value']

    return None
