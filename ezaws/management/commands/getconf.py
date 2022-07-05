import json
from django.utils import timezone
from django.core.management.base import BaseCommand
from web.models import Customer, Infrastructure
from web.utils import get_customers, get_customer, get_client, get_session

SILENT, NORMAL, VERBOSE = 0, 1, 2
verbosity = NORMAL
cur_date = None

class Command(BaseCommand):
    help = (
        "Get configuration objects from AWS account and store them in database"
    )

    def handle(self, *args, **options):
        global verbosity
        verbosity = options.get("verbosity", NORMAL)

        if verbosity >= NORMAL:
            self.stdout.write("Start import")

        # Loop on Customers which infrastructure must be saved
        customers = get_customers()
        for customer in customers:
            cust = get_customer(customer)
            if cust.is_active:
                self.stdout.write(cust.name)
                _get_infrastructure(cust)

        if verbosity >= NORMAL:
            self.stdout.write("End import")

def _get_infrastructure(customer):
    global cur_date
    cur_date = timezone.now()

    _get_instances(customer)
    _get_security_groups(customer)
    _get_iam_roles(customer)
    _get_volumes(customer)
    _get_snapshots(customer)
    _get_elbs(customer)
    _get_target_groups(customer)
    _get_autoscaling(customer)
    _get_cloudfront(customer)
    # S3 bucket
    # SNS
    # SQS
    # Lambda
    # RDS

def _get_instances(customer):
    client = get_client(customer, 'ec2')
    try:
        instances = client.describe_instances()
        if verbosity >= VERBOSE:
            print(instances)

        _save_object(customer, cur_date, 'instances', instances)

        for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                _save_object(customer, cur_date, 'instance', instance)

    except Exception as e:
        print(f'Failed to get instances of customer {customer.name}')
        print(e)

def _get_security_groups(customer):
    client = get_client(customer, 'ec2')
    try:
        sec_groups = client.describe_security_groups()
        if verbosity >= VERBOSE:
            print(sec_groups)

        _save_object(customer, cur_date, 'security_groups', sec_groups)

        for sec_group in sec_groups['SecurityGroups']:
            _save_object(customer, cur_date, 'security_group', sec_group)
    except Exception as e:
        print(f'Failed to get security groups of customer {customer.name}')
        print(e)

def _get_iam_roles(customer):
    client = get_client(customer, 'iam')
    try:
        roles = client.list_roles()
        if verbosity >= VERBOSE:
            print(roles)

        _save_object(customer, cur_date, 'roles', roles)

        for role in roles['Roles']:
            _save_object(customer, cur_date, 'role', role)
    except Exception as e:
        print(f'Failed to get roles of customer {customer.name}')
        print(e)

def _get_volumes(customer):
    client = get_client(customer, 'ec2')
    try:
        volumes = client.describe_volumes()
        if verbosity >= VERBOSE:
            print(volumes)

        _save_object(customer, cur_date, 'volumes', volumes)

        for volume in volumes['Volumes']:
            _save_object(customer, cur_date, 'volume', volume)
    except Exception as e:
        print(f'Failed to get volumes of customer {customer.name}')
        print(e)

def _get_snapshots(customer):
    client = get_client(customer, 'ec2')
    try:
        snapshots = client.describe_snapshots(OwnerIds=['self'])
        if verbosity >= VERBOSE:
            print(snapshots)

        _save_object(customer, cur_date, 'snapshots', snapshots)

        for snapshot in snapshots['Snapshots']:
            _save_object(customer, cur_date, 'snapshot', snapshot)
    except Exception as e:
        print(f'Failed to get snapshots of customer {customer.name}')
        print(e)

def _get_elbs(customer):
    client = get_client(customer, 'elb')
    try:
        elbs = client.describe_load_balancers()
        if verbosity >= VERBOSE:
            print(elbs)

        _save_object(customer, cur_date, 'elbs', elbs)
    except Exception as e:
        print(f'Failed to get elbs of customer {customer.name}')
        print(e)

    client = get_client(customer, 'elbv2')
    try:
        elbs = client.describe_load_balancers()
        if verbosity >= VERBOSE:
            print(elbs)

        _save_object(customer, cur_date, 'elbv2s', elbs)

        for elb in elbs['LoadBalancers']:
            _save_object(customer, cur_date, 'elbv2', elb)
            attrs = client.describe_load_balancer_attributes(LoadBalancerArn=elb['LoadBalancerArn'])
            value = {'LoadBalancerArn': elb['LoadBalancerArn'], "Attributes": attrs}
            _save_object(customer, cur_date, 'elbv2_attrs', value)

        for elb in elbs['LoadBalancers']:
            listeners = client.describe_listeners(LoadBalancerArn=elb['LoadBalancerArn'])
            _save_object(customer, cur_date, 'elbv2_listeners', listeners)

        for listener in listeners['Listeners']:
            rules = client.describe_rules(ListenerArn=listener['ListenerArn'])
            value = {'ListenerArn': listener['ListenerArn'], "Rules": rules}

            _save_object(customer, cur_date, 'elbv2_rules', value)

        # TODO: describe_listener_certificates ?

    except Exception as e:
        print(f'Failed to get elbv2s of customer {customer.name}')
        print(e)

def _get_target_groups(customer):
    client = get_client(customer, 'elbv2')
    try:
        target_groups = client.describe_target_groups()
        if verbosity >= VERBOSE:
            print(target_groups)

        _save_object(customer, cur_date, 'target_groups', target_groups)

        for target_group in target_groups['TargetGroups']:
            _save_object(customer, cur_date, 'target_group', target_group)
    except Exception as e:
        print(f'Failed to get target groups of customer {customer.name}')
        print(e)

def _get_autoscaling(customer):
    client = get_client(customer, 'autoscaling')

    try:
        as_groups = client.describe_auto_scaling_groups()
        if verbosity >= VERBOSE:
            print(as_groups)

        _save_object(customer, cur_date, 'auto_scaling_groups', as_groups)

        for as_group in as_groups['AutoScalingGroups']:
            _save_object(customer, cur_date, 'auto_scaling_group', as_group)

        launch_configs = client.describe_launch_configurations()
        if verbosity >= VERBOSE:
            print(launch_configs)

        _save_object(customer, cur_date, 'launch_configurations', launch_configs)

        for launch_config in launch_configs['LaunchConfigurations']:
            _save_object(customer, cur_date, 'launch_configuration', launch_config)
    except Exception as e:
        print(f'Failed to get autoscaling groups of customer {customer.name}')
        print(e)

def _get_cloudfront(customer):
    client = get_client(customer, 'cloudfront')

    try:
        distributions = client.list_distributions()
        if verbosity >= VERBOSE:
            print(distributions)

        _save_object(customer, cur_date, 'distributions', distributions)

        if 'Items' in distributions['DistributionList']:
            for distribution in distributions['DistributionList']['Items']:
                _save_object(customer, cur_date, 'distribution', distribution)
    except Exception as e:
        print(f'Failed to get cloudfront distribution of customer {customer.name}')
        print(e)


def _save_object(customer, date, object_type, object_value):
    infra_object = Infrastructure(
        customer=customer,
        date=date,
        object_type=object_type,
        object_value=json.dumps(object_value, default=str)
    )
    infra_object.save()
