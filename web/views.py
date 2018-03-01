import collections
import logging
from django.utils import timezone
from datetime import datetime, timedelta
from django.utils.translation import ugettext as _
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from . import utils
from . import cache
import aws.pricing as pricing
import aws.definitions as awsdef
from . import checks as ck
from .decorators import user_is_owner, console_defined, aws_creds_defined

std_logger = logging.getLogger('general')


@login_required
def index(request):
    names = utils.get_customers()
    context = { 'names': names }
    return render(request, 'index.html', context)


@login_required
@user_is_owner
@console_defined
def goto_console(request, cust_name):
    customer = utils.get_customer(cust_name)
    #return redirect(customer.console_url)
    return HttpResponseRedirect(customer.console_url)


@login_required
@user_is_owner
@aws_creds_defined
def get_instances(request, cust_name):
    names = utils.get_customers()
    customer = utils.get_customer(cust_name)
    client = utils.get_client(customer, 'ec2')
    session = utils.get_session(customer)
    costs = pricing.Pricing(customer.region)

    ec2list = []
    context = {'current': cust_name, 'names': names, 'ec2list': ec2list, 'running_count': 0, 'price': 0}

    ec2 = session.resource('ec2')
    try:
        ips = client.describe_addresses()
        std_logger.debug("EC2 IPs=", ips)
    except Exception as e:
        messages.error(request, e)
        utils.check_perm_message(request, cust_name)
        return render(request, 'instances.html', context)

    try:
        amis = list(ec2.images.filter(Owners=['self']))
    except Exception as e:
        messages.error(request, e)
        utils.check_perm_message(request, cust_name)
        return render(request, 'instances.html', context)

    try:
        for inst in ec2.instances.all():
            if utils.instance_is_running(inst):
                context['running_count'] += 1

            name = utils.get_instance_name(inst, customer.aws_resource_tag_name) or ''

            ec2list.append({'instance_id': inst.id,
                            'instance_type': inst.instance_type,
                            'instance_state': inst.state,
                            'image_id': inst.image_id,
                            'image_name': _get_ami_name(amis, inst.image_id, customer.aws_resource_tag_name),
                            'public_ip': inst.public_ip_address,
                            'is_elastic': _is_elastic_ip(ips, inst.public_ip_address),
                            'private_ip': inst.private_ip_address,
                            'zone': inst.placement['AvailabilityZone'],
                            'tags': inst.tags,
                            'name': name,
                            'volume_size': 0})

            if inst.instance_type in pricing.ec2_pricing and utils.instance_is_running(inst):
                context['price'] += int(costs.get_EC2_cost_per_hour(inst.instance_type))
    except Exception as e:
        messages.error(request, e)
        utils.check_perm_message(request, cust_name)
        return render(request, 'instances.html', context)

    try:
        vol_size = collections.defaultdict(int)
        volumes = ec2.volumes.all()
        for vol in volumes:
            if not len(vol.attachments):
                continue
            inst_id = vol.attachments[0]['InstanceId']
            vol_size[inst_id] += vol.size

        for inst in ec2list:
            inst['volume_size'] = vol_size[inst['instance_id']]
    except Exception as e:
        messages.error(request, e)
        utils.check_perm_message(request, cust_name)
        return render(request, 'instances.html', context)

    return render(request, 'instances.html', context)


@login_required
@user_is_owner
@aws_creds_defined
def get_reserved_instances(request, cust_name):
    names = utils.get_customers()
    customer = utils.get_customer(cust_name)
    client = utils.get_client(customer, 'ec2')
    session = utils.get_session(customer)
    costs = pricing.Pricing(customer.region)

    rsvlist = []
    context = {'current': cust_name, 'names': names, 'rsvlist': rsvlist, 'price': 0 }
    now = timezone.now()

    try:
        #rsvlist = client.describe_reserved_instances(Filters=[ {'Name': 'availability-zone', 'Values':[ customer.region ]}] )
        rsvds = client.describe_reserved_instances(Filters=[{'Name': 'state', 'Values': ['active']}])

        for rsv in rsvds['ReservedInstances']:
            rsvlist.append({
                'reservedInstancesId': rsv['ReservedInstancesId'],
                'productDescription': rsv['ProductDescription'],
                'fixedPrice': int(rsv['FixedPrice']),
                'monthlyPrice': int(rsv['RecurringCharges'][0]['Amount'] * 24 * 31),
                #'monthlyPrice': int(rsv['UsagePrice'] * 24 * 31),
                'scope': rsv['Scope'],
                'offeringClass': rsv['OfferingClass'],
                'tenancy': rsv['InstanceTenancy'],
                'offeringType': rsv['OfferingType'],
                'instanceCount': rsv['InstanceCount'],
                'instanceType': rsv['InstanceType'],
                #'availabilityZone': rsv['AvailabilityZone'],
                'endtime': rsv['End'],
                'timealert': 'danger' if rsv['End'] <= now else ('warning' if rsv['End'] > now - timedelta(30) else 'success')
            })
    except Exception as e:
        messages.error(request, e)
        utils.check_perm_message(request, cust_name)
        return render(request, 'reserved_instances.html', context)

    # Check usage towards running EC2 Instances
    try:
        ec2 = session.resource('ec2')
        rsv_allocation, unused_ec2 = ck.check_reserved_instances(customer, rsvds['ReservedInstances'], list(ec2.instances.all()))
        for rsv in rsvlist:
            rsv['allocated_ec2'] = rsv_allocation[rsv['reservedInstancesId']]
    except Exception as e:
        messages.error(request, e)
        utils.check_perm_message(request, cust_name)
        return render(request, 'instances.html', context)

    return render(request, 'reserved_instances.html', context)


@login_required
@user_is_owner
@aws_creds_defined
def get_volumes(request, cust_name):
    names = utils.get_customers()
    customer = utils.get_customer(cust_name)
    session = utils.get_session(customer)
    costs = pricing.Pricing(customer.region)

    vol_list = []

    ec2 = session.resource('ec2')

    context = { 'current': cust_name, 'names': names, 'vol_list': vol_list,
                'total_vols': 0, 'total_orphans': 0,
                'total_price': 0, 'total_size': 0 }

    try:
        inst_name_cache = _get_instances_name_cache(ec2, customer.aws_resource_tag_name)
        volumes = ec2.volumes.all()
        for vol in volumes:
            context['total_vols'] += 1
            context['total_size'] += vol.size
            context['total_price'] += costs.get_EBS_cost_per_month(vol.size, vol.volume_type, vol.iops)
            v = {'volume_id': vol.id, 'instance_id': 'N/A', 'instance_name': 'N/A',
                 'device': 'N/A', 'size': 0, 'read_ops': 'N/A', 'write_ops': 'N/A'}
            if not len(vol.attachments):
                context['total_orphans'] += 1
                continue
            if len(vol.attachments) and ('InstanceId' in vol.attachments[0]):
                v['instance_id'] = vol.attachments[0]['InstanceId']
                v['instance_name'] = inst_name_cache[v['instance_id']]
                v['device'] = vol.attachments[0]['Device']
            else:
                context['total_orphans'] += 1

            v['size'] = vol.size
            vol_list.append(v)
    except Exception as e:
        messages.error(request, e)
        utils.check_perm_message(request, cust_name)
        return render(request, 'volumes.html', context)

    return render(request, 'volumes.html', context)


# TODO: use the Paginator with the Snapshots
@login_required
@user_is_owner
@aws_creds_defined
def get_snapshots(request, cust_name):
    names = utils.get_customers()
    customer = utils.get_customer(cust_name)
    client = utils.get_client(customer, 'ec2')
    costs = pricing.Pricing(customer.region)

    snaplist = []
    vol_ids = []
    context = { 'current': cust_name, 'names': names, 'snaplist': snaplist,
                'total_max_size': 0, 'total_max_price': 0,
                'total_min_size': 0, 'total_min_price': 0 }

    try:
        response = client.describe_snapshots(OwnerIds=[customer.owner_id])
    except Exception as e:
        messages.error(request, e)
        utils.check_perm_message(request, cust_name)
        return render(request, 'snapshots.html', context)

    snapshot_list = response['Snapshots']

    for snap in snapshot_list:
        snaplist.append(snap)
        context['total_max_size'] += snap['VolumeSize']
        context['total_max_price'] += costs.get_EBS_cost_per_month(snap['VolumeSize'], 'snapshot')
        if snap['VolumeId'] not in vol_ids:
            vol_ids.append(snap['VolumeId'])
            context['total_min_size'] += snap['VolumeSize']
            context['total_min_price'] += costs.get_EBS_cost_per_month(snap['VolumeSize'], 'snapshot')

    return render(request, 'snapshots.html', context)


@login_required
@user_is_owner
@aws_creds_defined
def check_snapshots(request, cust_name):
    names = utils.get_customers()
    customer = utils.get_customer(cust_name)
    session = utils.get_session(customer)
    ec2 = session.resource('ec2')
    client = utils.get_client(customer, 'ec2')

    ec2list = []
    ec2vol = {}
    context = {'current': cust_name, 'names': names, 'ec2list': ec2list}

    try:
        response = client.describe_snapshots(OwnerIds=[customer.owner_id])
    except Exception as e:
        messages.error(request, e)
        utils.check_perm_message(request, cust_name)
        return render(request, 'check_snapshots.html', context)

    snapshot_list= response['Snapshots']

    # Algo : loop on EC2 instances to get the Volumes ID
    #           loop on the Snapshots to check if the Volume ID match
    # Must determine if an EC2 instance is snapshoted or no, fully or partially
    # also get the date of last snapshot
    try:
        for inst in ec2.instances.all():
            ec2vol[inst.id] = { 'all': [] }
            name = utils.get_instance_name(inst, customer.aws_resource_tag_name) or ''

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
    except Exception as e:
        messages.error(request, e)
        utils.check_perm_message(request, cust_name)
        return render(request, 'check_snapshots.html', context)

    return render(request, 'check_snapshots.html', context)


@login_required
@user_is_owner
@aws_creds_defined
def get_elbs(request, cust_name):
    names = utils.get_customers()
    customer = utils.get_customer(cust_name)
    client = utils.get_client(customer, 'elb')
    costs = pricing.Pricing(customer.region)

    elblist = []
    price = 0
    context = {'current': cust_name, 'names': names, 'elblist': elblist, 'price': 0}

    try:
        elbs = client.describe_load_balancers()
    except Exception as e:
        messages.error(request, e)
        utils.check_perm_message(request, cust_name)
        return render(request, 'elbs.html', context)

    session = utils.get_session(customer)
    ec2 = session.resource('ec2')   # to get the instance Name from instance ID
    try:
        inst_name_cache = _get_instances_name_cache(ec2, customer.aws_resource_tag_name)
    except Exception as e:
        messages.error(request, e)
        utils.check_perm_message(request, cust_name)
        return render(request, 'elbs.html', context)

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
            'arn': elb['LoadBalancerName'],
            'type': 'classic',
            'DNSName': elb['DNSName'],
            'listeners': listeners,
            'instances': instances,
            'target_groups': [],
            'zones': [],
        })
        context['price'] += costs.get_ELB_cost_per_hour('classic')

    # Applicative ELB
    client = utils.get_client(customer, 'elbv2')
    elbs = client.describe_load_balancers()
    try:
        target_groups = client.describe_target_groups()
    except Exception as e:
        messages.error(request, e)
        utils.check_perm_message(request, cust_name)
        target_groups = { 'TargetGroups' : [] }

    target_health = {}

    for elb in elbs['LoadBalancers']:
        e = {
            'name': elb['LoadBalancerName'],
            'arn': elb['LoadBalancerArn'],
            'type': elb['Type'],
            'DNSName': elb['DNSName'],
            'listeners': [],
            'instances': [],
            'target_groups': [],
            'zones': [],
        }
        listeners = client.describe_listeners(LoadBalancerArn=elb['LoadBalancerArn'])
        for list in listeners['Listeners']:
            e['listeners'].append(list['Port'])

        for tgt in target_groups['TargetGroups']:
            for arn in tgt['LoadBalancerArns']:
                if elb['LoadBalancerArn'] == arn:
                    tgt_name = tgt['TargetGroupName']
                    e['target_groups'].append(tgt_name)

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
        e['listeners'] = sorted(e['listeners'])
        elblist.append(e)

        context['price'] += costs.get_ELB_cost_per_hour('application')

    # Determine the R53 Domains associated with each ELB
    zones_rsets = cache.get_domains(request, customer)
    if zones_rsets:
        for zone, rsets in zones_rsets.items():
            #print(zone)
            for rset in rsets:
                if rset['Type'] == 'A':
                    if 'AliasTarget' in rset:
                        #print('AliasTarget:', rset['Name'], rset['Type'], rset['AliasTarget']['DNSName'])
                        _find_elb(rset['Name'], rset['AliasTarget']['DNSName'], elblist)
                elif rset['Type'] == 'CNAME' and 'ResourceRecords' in rset:
                    for rr in rset['ResourceRecords']:
                        #print('CNAME Value:', rset['Name'], rr['Value'])
                        _find_elb(rset['Name'], rr['Value'], elblist)

    return render(request, 'elbs.html', context)


def _find_elb(rr_name, value, elblist):
    '''Modify elblist if ELB name found in "name"'''
    for elb in elblist:
        if elb['DNSName'] in value:
            domain = rr_name.rstrip('.')
            domain = '.'.join(domain.split('.')[-2:])
            if domain not in elb['zones']:
                elb['zones'].append(domain)


@login_required
@user_is_owner
@aws_creds_defined
def get_elasticache(request, cust_name):
    names = utils.get_customers()
    customer = utils.get_customer(cust_name)
    client = utils.get_elasticache(customer)
    costs = pricing.Pricing(customer.region)

    def _wrap():
        cachelist = []
        total_price = 0

        try:
            caches = client.describe_cache_clusters()
        except Exception as e:
            messages.error(request, e)
            utils.check_perm_message(request, cust_name)
            return 0, cachelist

        for cache in caches['CacheClusters']:
            price = costs.get_ElastiCache_cost_per_hour(cache['CacheNodeType'][len('cache.'):])
            cachelist.append({
                'name': cache['CacheClusterId'],
                'type': cache['CacheNodeType'][len('cache.'):], # strip "cache." from "cache.t2.micro"
                'engine': cache['Engine'],
                'engineVersion': cache['EngineVersion'],
                'numnodes': cache['NumCacheNodes'],
                'availzone': cache['PreferredAvailabilityZone'],
                'price': price,
            })

            total_price += price

        return total_price, cachelist

    (price, cachelist) = _wrap()
    return render(request, 'elasticache.html', {'current': cust_name, 'names': names, 'cachelist': cachelist, 'price': price })


def _is_elastic_ip(ips, public_ip):
    if not 'Addresses' in ips: return False
    for ip in ips['Addresses']:
        if 'PublicIp' in ip and ip['PublicIp'] == public_ip: return True
    return False


def _get_instances_name_cache(ec2, tag_name='NAME'):
    '''Returns a dict with inst_id as a key and instance Name as value'''
    cache = collections.defaultdict(str)
    for inst in ec2.instances.all():
        cache[inst.instance_id] = utils.get_instance_name(inst, tag_name) or inst.instance_id

    return cache

def _get_ami_name(amis, ami_id, tag_name='NAME'):
    for ami in amis:
        if ami.id == ami_id:
            return utils.get_ami_name(ami, tag_name)

    return 'N/A'


