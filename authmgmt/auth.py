import os
import json
import logging
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.utils.translation import ugettext as _
from django.http import HttpResponseRedirect, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from .forms import LoginForm, SubscribeForm, ProfileForm
from web.models import User, Customer
from web.utils import get_customer, get_customers

std_logger = logging.getLogger('general')


def indexAction(request):
    return render(request, 'index.html')


def signupAction(request):
    if request.method == 'POST':
        form = SubscribeForm(request.POST)
        if form.is_valid():
            n = form.cleaned_data['username']
            p = form.cleaned_data['password']
            p2 = form.cleaned_data['password2']
            e = form.cleaned_data['email']

            # Consistency checks :
            # username must be unique
            # passwords must match
            if p != p2:
                messages.error(request, _('Passwords mismatch, please enter your Password again'))
            try:
                user = User.objects.get(username=n)
                messages.error(request, _('This Username already exists, please choose another one !'))
                return render(request, 'subscribe.html', {'form': form})
            except Exception as exc:
                pass

            # Create User
            user = User.objects.create_user(n, e, p)
            user = authenticate(username=n, password=p, request=request)
            customer = Customer()
            customer.name = n
            customer.save()
            customer.admins.add(user)
            login(request, user)
            request.session['customer'] = n
            messages.info(request, _(
                'Your Account has been created successfully ! Click <a href="/auth/profile">here</a> to complete your Profile'),
                          extra_tags='safe')
            request.session['timezone'] = 'UTC'
            return HttpResponseRedirect('/web')
        else:
            messages.error(request, _('Invalid Form Values'))
    else:
        form = SubscribeForm()

    return render(request, 'subscribe.html', {'form': form})


def loginAction(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if request.session.test_cookie_worked():
            request.session.delete_test_cookie()
        else:
            return HttpResponse("Please enable cookies and try again.")

        if form.is_valid():
            n = form.cleaned_data['username']
            p = form.cleaned_data['password']
            user = authenticate(username=n, password=p, request=request)
            if user is not None:
                login(request, user)
                try:
                    messages.info(request, _('Authentication successfull !'))
                    # Set the Customer name in Session
                    customers = list(user.customer_set.filter(admins=user.id))
                    if len(customers):
                        tz = customers[0].timezone if customers[0].timezone else 'UTC'
                        timezone.activate(tz)
                        request.session['timezone'] = tz
                        request.session['customer'] = customers[0].name
                        request.session['zone'] = customers[0].region
                        std_logger.debug("Customer=" + request.session['customer'] + " Zone=" + request.session['zone'])

                    return HttpResponseRedirect('/web')
                except Exception as e:
                    messages.error(request, _('Something wrent wrong - internal error, please contact the Technical Support'))
                    messages.error(request, e)
            else:
                messages.error(request, _('Authentication failed - either your Login or your Password is incorrect'))
        else:
            messages.error(request, _('Invalid Form Values'))
    else:
        form = LoginForm()

    request.session.set_test_cookie()
    return render(request, 'login.html', { 'form': form })


def logoutAction(request):
    logout(request)
    return HttpResponseRedirect('/')


@login_required
def editProfileAction(request):
    customer = get_customer(request.user.username)

    if request.method == 'POST':
        if 'cancel' in request.POST:
            return HttpResponseRedirect('/web')

        form = ProfileForm(request.POST)
        if form.is_valid():
            customer.console_url = form.cleaned_data['console_url']
            customer.access_key = form.cleaned_data['access_key']
            customer.secret_key = form.cleaned_data['secret_key']
            customer.owner_id = form.cleaned_data['owner_id']
            customer.region = form.cleaned_data['region']
            customer.timezone = form.cleaned_data['timezone']
            try:
                customer.save()
                messages.info(request, _("Your settings has been successfully updated !"))
            except Exception as e:
                std_logger.error("Error while updating Customer profile: ", e)
                messages.error(request, _("Sorry, an error has been detected while updating your settings !"))
    else:
        form = ProfileForm(
            initial={
                'console_url': customer.console_url,
                'access_key': customer.access_key,
                'secret_key': customer.secret_key,
                'owner_id': customer.owner_id,
                'region': customer.region,
                'timezone': customer.timezone,
            }
        )

    return render(request, 'profile.html', { 'form': form, 'next': request.GET.get('next', '') })


@login_required
def changePasswordAction(request):
    if request.method == 'POST':
        if 'cancel' in request.POST:
            return HttpResponseRedirect('/web')

        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, 'Your password was successfully updated!')
            return HttpResponseRedirect('/web')
        else:
            messages.error(request, 'Please correct the error below.')

    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'change_password.html', { 'form': form })


@login_required
def checkKeyAction(request, cust_name):
    names = get_customers()

    perms = [
        { 'perm': 'ec2_describe_addresses', 'iam_perm': 'ec2:DescribeAddresses', 'desc': 'List Elastic IP' },
        { 'perm': 'ec2_describe_instances', 'iam_perm': 'ec2:DescribeInstances', 'desc': 'List Instances' },
        { 'perm': 'ec2_describe_volumes', 'iam_perm': 'ec2:DescribeVolumes', 'desc': 'List Volumes' },
        { 'perm': 'ec2_describe_snapshots', 'iam_perm': 'ec2:DescribeSnapshots', 'desc': 'List Snapshots' },
        { 'perm': 'ec2_describe_images', 'iam_perm': 'ec2:DescribeImages', 'desc': 'List Images' },
        { 'perm': 'cw_get_metrics_statistics', 'iam_perm': 'cloudwatch:GetMetricStatistics', 'desc': 'Get Metrics' },
        { 'perm': 'elb_describe_loadbalancers', 'iam_perm': 'elasticloadbalancing:DescribeLoadBalancers', 'desc': 'List Load-Balancers' },
        { 'perm': 'elb_describe_target_groups', 'iam_perm': 'elasticloadbalancing:DescribeTargetGroups', 'desc': 'List Target Groups'},
        { 'perm': 'route53_list_hosted_zones', 'iam_perm': 'route53:ListHostedZones', 'desc': 'List Hosted Zones'},
        { 'perm': 'route53_list_resources_record_sets', 'iam_perm': 'route53:ListResourceRecordSets', 'desc': 'List Resource Record Sets'},
        { 'perm': 'elasticache_describe_clusters', 'iam_perm': 'elasticache:DescribeCacheClusters', 'desc': 'List Cache Clusters' },
    ]

    return render(request, 'check_key.html', context = {'current': cust_name, 'names': names, 'perms': perms })


@csrf_exempt
def hookDeployAction(request):
    # Should be in another Controller - normally called by DockerHub as a hook
    json_data = json.loads(request.body)
    tag = json_data['push_data']['tag']

    #os.system('sudo -u ezaws /home/ezaws/restart.sh')
    os.system('/home/ezaws/restart.sh ' + tag)
    return HttpResponse("OK")


