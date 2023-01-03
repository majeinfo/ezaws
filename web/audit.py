import os
import glob
import re
from datetime import datetime
from django.utils.translation import gettext as _
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.urls import reverse
from django.core.mail import send_mail
from . import utils
from .models import Customer
from .decorators import user_is_owner, aws_creds_defined
from . import checks as ck
from . import cache
from . import log


# TODO: should be called locally
def cronAuditAllCustomersAction(request):
    names = _get_customers()
    for cust_name in names:
        cronAuditAction(request, cust_name)

    send_mail(
        'EZAWS Audit all customers',
        'Adutis done.',
        'ezaws@delamarche.com',
        ['ezaws@delamarche.com'],   # TODO: mail should be sent to customer
        fail_silently=False,
    )

    return HttpResponse("Done")


# TODO: should be called locally
# TODO: audit reports should not be stored in the web server tree
def cronAuditAction(request, cust_name):
    resp = _auditAction(request, cust_name)
    #print(resp.content)

    # Store the audit
    target_dir = _get_audit_report_dir(cust_name)
    if not os.path.isdir(target_dir):
        try:
            os.mkdir(target_dir)
        except Exception as e:
            # TODO: Store a cron error log
            return HttpResponse(f"Could not create directory {target_dir}: {e}")

    d = datetime.now()
    rel_fname = "audit-" + d.strftime("%y%m%d") + ".html"
    abs_fname = os.path.join(target_dir, rel_fname)

    try:
        with open(abs_fname, "wb") as f:
            f.write(resp.content)
    except Exception as e:
        # TODO: store a cron error log
        return HttpResponse(f"Could not create audit report {abs_fname}: {e}")

    return HttpResponse("OK")


@login_required
@user_is_owner
@aws_creds_defined
def viewAuditReportsAction(request, cust_name):
    names = _get_customers()
    context = {
        'current': cust_name, 'names': names, 'reports': [],
    }
    target_dir = _get_audit_report_dir(cust_name)
    date_re = re.compile('.*audit-(..)(..)(..)\.html')
    for report in sorted(glob.glob(os.path.join(target_dir, 'audit-*.html'))):
        re_res = date_re.search(report)
        try:
            audit_date = f"{re_res.group(3)}/{re_res.group(2)}/20{re_res.group(1)}"
            audit_url = reverse('view_audit_report_action', kwargs={'cust_name': cust_name, 'report_name': f"{re_res.group(1)}{re_res.group(2)}{re_res.group(3)}"})
            context['reports'].append({ 'date': audit_date, 'url': audit_url })
        except Exception as e:
            continue

    return render(request, 'view_audit_reports.html', context)


@login_required
@user_is_owner
@aws_creds_defined
def viewAuditReportAction(request, cust_name, report_name):
    resp = HttpResponse()
    target_dir = _get_audit_report_dir(cust_name)
    abs_fname = os.path.join(target_dir, "audit-" + report_name + ".html")
    try:
        with open(abs_fname, "rb") as f:
            resp.content = f.read()
    except Exception as e:
        resp.content = b"An error occurred"

    return resp


def _get_audit_report_dir(cust_name):
    return os.path.join(settings.CRON_DIR, cust_name)


@login_required
@user_is_owner
@aws_creds_defined
def auditAction(request, cust_name):
    return _auditAction(request, cust_name)


def _auditAction(request, cust_name):
    log.log_time('-> auditAction')
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
        'total_amis': 'N/A', 'orphan_amis': {}, 'total_amis_size': 'N/A', 'total_amis_price': 'N/A',
        'total_eips': 'N/A', 'orphan_eips': [], 'total_eips_price': 'N/A',
        'total_instances': 'N/A', 'stopped_instances': [], 'total_instances_price': 'N/A', 'total_instances_size': 'N/A',
        'orphan_target_groups': [],
        'underused_volumes': [], 'underused_size': 'N/A', 'underused_price': 'N/A',
        'long_time_stopped_instances': [], 'long_time_stopped_inst_vol_size': 0, 'long_time_stopped_inst_vol_price': 0,
        'total_ri': 0, 'ri_not_filled': {}, 'ec2_without_ri': [],
        'instances_usage': [],
        'total_obsolete_volumes': 0, 'obsolete_volumes': [],
        'orphan_rds_snapshots': [],
    }

    # Check for Orphan RDS Snapshots
    context['orphan_rds_snapshots'] = ck.check_orphan_rds_snapshots(customer)

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

    # Check obsolete Volumes
    result = ck.check_obsolete_volumes(customer, volumes, instances)
    context['total_obsolete_volumes'] = result['total']
    context['obsolete_volumes'] = result['volumes']

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
        context['orphan_amis'] = result['ami_attrs']
        context['total_amis'] = len(amis)
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

    # Analyse Instances Usage
    buckets = ck.check_instances_usage(customer, instances)
    context['instances_usage'] = buckets

    log.log_time('<- auditAction')
    return render(request, 'audit.html', context)


def _add_values(*args):
    values = []
    for t in zip(*args):
        values.append(sum(*t))

    return values


def _get_customers():
    queryset = Customer.objects.all()
    names = []
    for q in queryset: names.append(q.name)
    return sorted(names)


def _get_customer(cust_name):
    customer = Customer.objects.get(name=cust_name)
    return customer


