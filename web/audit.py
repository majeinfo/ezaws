from django.utils.translation import ugettext as _
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from . import utils
from .models import Customer
from .decorators import user_is_owner, aws_creds_defined
from . import checks as ck
import aws.params as p
from . import cache

@login_required
@user_is_owner
@aws_creds_defined
def auditAction(request, cust_name):
    names = _get_customers()
    customer = _get_customer(cust_name)

    # Get resources
    session = utils.get_session(customer)
    ec2 = session.resource('ec2')
    client = utils.get_client(customer, 'ec2')

    # Initialize Response Context
    context = {
        'current': cust_name, 'names': names,
        'total_vols': 'N/A', 'orphan_vols': [], 'total_vols_size': 'N/A', 'vol_sizes': 'N/A', 'total_vols_price': 'N/A',
        'total_amis': 'N/A', 'orphan_amis': [], 'total_amis_size': 'N/A', 'ami_sizes': 'N/A', 'total_amis_price': 'N/A',
        'total_eips': 'N/A', 'orphan_eips': [], 'total_eips_price': 'N/A',
        'total_instances': 'N/A', 'stopped_instances': [], 'total_instances_price': 'N/A', 'total_instances_size': 'N/A',
        'orphan_target_groups': [],
        'underused_volumes': [], 'underused_size': 'N/A', 'underused_price': 'N/A',
        'long_time_stopped_instances': [], 'long_time_stopped_inst_vol_size': 0, 'long_time_stopped_inst_vol_price': 0,
        'total_ri': 0, 'ri_not_filled': {}, 'ec2_without_ri': [],
    }

    # Get instances
    try:
        instances = list(ec2.instances.all())
    except Exception as e:
        messages.error(request, e)
        utils.check_perm_message(request, cust_name)
        return render(request, 'audit.html', context)

    # Check Orphan Volumes
    volumes = cache.get_volumes(request, customer)
    if volumes:
        result = ck.check_orphan_volumes(customer, volumes)
        context['orphan_vols'] = result['orphans']
        context['total_vols'] = len(volumes)
        context['vol_sizes'] = result['vol_sizes']
        context['total_vols_size'] = result['total_size']
        context['total_vols_price'] = int(result['total_price'])
    else:
        utils.check_perm_message(request, cust_name)
        return render(request, 'audit.html', context)

    # Check underused Volumes
    try:
        result = ck.check_underused_volume(customer, volumes, instances)
        context['underused_volumes'] = result['underused_volumes']
        context['underused_size'] = result['underused_size']
        context['underused_price'] = result['underused_price']
    except Exception as e:
        messages.error(request, e)
        utils.check_perm_message(request, cust_name)
        return render(request, 'audit.html', context)

    # Check Orphan AMIs
    amis = None
    try:
        amis = list(ec2.images.filter(Owners=['self']))
        result = ck.check_orphan_amis(customer, amis, instances)
        #print(result)
        context['orphan_amis'] = result['orphans']
        context['total_amis'] = len(amis)
        context['ami_sizes'] = result['ami_sizes']
        context['total_amis_size'] = result['total_size']
        context['total_amis_price'] = result['total_price']
    except Exception as e:
        messages.error(request, e)
        utils.check_perm_message(request, cust_name)
        return render(request, 'audit.html', context)

    # Check Orphan EIPs
    eips = None
    try:
        eips = session.client('ec2').describe_addresses()
        result = ck.check_orphan_eips(customer, eips['Addresses'])
        #print(result)
        context['total_eips'] = len(eips['Addresses'])
        context['orphan_eips'] = result['orphans']
        context['total_eips_price'] = result['total_price']
    except Exception as e:
        messages.error(request, e)
        utils.check_perm_message(request, cust_name)
        return render(request, 'audit.html', context)

    # Check Orphan Target Groups
    try:
        target_groups = session.client('elbv2').describe_target_groups()
        result = ck.check_orphan_target_groups(customer, target_groups)
        context['orphan_target_groups'] = result['orphans']
        context['total_target_groups'] = len(target_groups['TargetGroups'])
    except Exception as e:
        messages.error(request, e)
        utils.check_perm_message(request, cust_name)
        return render(request, 'audit.html', context)

    # Check stopped instances
    try:
        result = ck.check_stopped_instances(customer, instances, volumes)
        context['stopped_instances'] = result['stopped_inst']
        context['total_instances'] = len(instances)
        context['total_instances_price'] = result['total_price']
        context['total_instances_size'] = result['total_size']
    except Exception as e:
        messages.error(request, e)
        utils.check_perm_message(request, cust_name)
        return render(request, 'audit.html', context)

    # Check for old and stopped Instances
    try:
        result = ck.check_long_time_stopped_instances(customer, instances)
        context['long_time_stopped_instances'] = result['long_time_stopped_inst']
        for inst in context['long_time_stopped_instances']:
            size, price = utils.get_ec2_volume_size_price(customer, inst, volumes)
            context['long_time_stopped_inst_vol_size'] += size
            context['long_time_stopped_inst_vol_price'] += price
    except Exception as e:
        messages.error(request, e)
        utils.check_perm_message(request, cust_name)
        return render(request, 'audit.html', context)

    # Analyze the RI usage
    try:
        rsvds = client.describe_reserved_instances(Filters=[{'Name': 'state', 'Values': ['active']}])
        context['total_ri'] = len(rsvds)
    except Exception as e:
        messages.error(request, e)
        utils.check_perm_message(request, cust_name)
        return render(request, 'audit.html', context)

    try:
        rsv_allocation, unused_ec2 = ck.check_reserved_instances(customer, rsvds['ReservedInstances'], list(ec2.instances.all()))
        not_filled = {}
        for rsv_id, value in rsv_allocation.items():
            if value['remaining_size']:
                not_filled[rsv_id] = value['remaining_size']
        context['ri_not_filled'] = not_filled
        context['ec2_without_ri'] = unused_ec2
    except Exception as e:
        messages.error(request, e)
        utils.check_perm_message(request, cust_name)
        return render(request, 'audit.html', context)

    return render(request, 'audit.html', context)


def _get_customers():
    queryset = Customer.objects.all()
    names = []
    for q in queryset: names.append(q.name)
    return sorted(names)


def _get_customer(cust_name):
    customer = Customer.objects.get(name=cust_name)
    return customer

