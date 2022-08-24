import json
import logging
from django.utils import timezone
from django.core.management.base import BaseCommand
from web.models import Infrastructure, InfraCollected
from web.utils import get_customers, get_customer, get_client, get_session

std_logger = logging.getLogger('commands')

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
        if verbosity >= VERBOSE:
            std_logger.setLevel(logging.DEBUG)

        std_logger.info("Start import")

        # Loop on Customers which infrastructure must be saved
        customers = get_customers()
        for customer in customers:
            cust = get_customer(customer)
            if cust.is_active:
                std_logger.info(cust.name)
                _get_infrastructure(cust)

        std_logger.info("End import")

def _get_infrastructure(customer):
    global cur_date
    cur_date = timezone.now()
    infra_collected = InfraCollected(customer=customer, date=cur_date)
    infra_collected.save()

    _get_instances(customer)
    _get_security_groups(customer)
    _get_iam_roles(customer)
    _get_volumes(customer)
    _get_snapshots(customer)
    _get_elbs(customer)
    _get_target_groups(customer)
    _get_autoscaling(customer)
    _get_cloudfront(customer)
    _get_route53(customer)
    # S3 bucket
    # SNS
    # SQS
    # Lambda
    # RDS

def _get_instances(customer):
    client = get_client(customer, 'ec2')
    try:
        instances = client.describe_instances()
        std_logger.debug(instances)

        _save_object(customer, cur_date, 'instances', instances)

        for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                _save_object(customer, cur_date, 'instance', instance)

    except Exception as e:
        std_logger.error(f'Failed to get instances of customer {customer.name}')
        std_logger.error(e)

def _get_security_groups(customer):
    client = get_client(customer, 'ec2')
    try:
        sec_groups = client.describe_security_groups()
        std_logger.debug(sec_groups)

        _save_object(customer, cur_date, 'security_groups', sec_groups)

        for sec_group in sec_groups['SecurityGroups']:
            _save_object(customer, cur_date, 'security_group', sec_group)
    except Exception as e:
        std_logger.error(f'Failed to get security groups of customer {customer.name}')
        std_logger.error(e)

def _get_iam_roles(customer):
    client = get_client(customer, 'iam')
    try:
        roles = client.list_roles()
        std_logger.debug(roles)

        _save_object(customer, cur_date, 'roles', roles)

        for role in roles['Roles']:
            _save_object(customer, cur_date, 'role', role)
    except Exception as e:
        std_logger.error(f'Failed to get roles of customer {customer.name}')
        std_logger.error(e)

def _get_volumes(customer):
    client = get_client(customer, 'ec2')
    try:
        volumes = client.describe_volumes()
        std_logger.debug(volumes)

        _save_object(customer, cur_date, 'volumes', volumes)

        for volume in volumes['Volumes']:
            _save_object(customer, cur_date, 'volume', volume)
    except Exception as e:
        std_logger.error(f'Failed to get volumes of customer {customer.name}')
        std_logger.error(e)

def _get_snapshots(customer):
    client = get_client(customer, 'ec2')
    try:
        snapshots = client.describe_snapshots(OwnerIds=['self'])
        std_logger.debug(snapshots)

        _save_object(customer, cur_date, 'snapshots', snapshots)

        for snapshot in snapshots['Snapshots']:
            _save_object(customer, cur_date, 'snapshot', snapshot)
    except Exception as e:
        std_logger.error(f'Failed to get snapshots of customer {customer.name}')
        std_logger.error(e)

def _get_elbs(customer):
    client = get_client(customer, 'elb')
    try:
        elbs = client.describe_load_balancers()
        std_logger.debug(elbs)

        _save_object(customer, cur_date, 'elbs', elbs)
    except Exception as e:
        std_logger.error(f'Failed to get elbs of customer {customer.name}')
        std_logger.error(e)

    client = get_client(customer, 'elbv2')
    try:
        elbs = client.describe_load_balancers()
        std_logger.debug(elbs)

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
        std_logger.error(f'Failed to get elbv2s of customer {customer.name}')
        std_logger.error(e)

def _get_target_groups(customer):
    client = get_client(customer, 'elbv2')
    try:
        target_groups = client.describe_target_groups()
        std_logger.debug(target_groups)

        _save_object(customer, cur_date, 'target_groups', target_groups)

        for target_group in target_groups['TargetGroups']:
            _save_object(customer, cur_date, 'target_group', target_group)
    except Exception as e:
        std_logger.error(f'Failed to get target groups of customer {customer.name}')
        std_logger.error(e)

def _get_autoscaling(customer):
    client = get_client(customer, 'autoscaling')

    try:
        as_groups = client.describe_auto_scaling_groups()
        std_logger.debug(as_groups)

        _save_object(customer, cur_date, 'auto_scaling_groups', as_groups)

        for as_group in as_groups['AutoScalingGroups']:
            _save_object(customer, cur_date, 'auto_scaling_group', as_group)

        launch_configs = client.describe_launch_configurations()
        std_logger.debug(launch_configs)

        _save_object(customer, cur_date, 'launch_configurations', launch_configs)

        for launch_config in launch_configs['LaunchConfigurations']:
            _save_object(customer, cur_date, 'launch_configuration', launch_config)
    except Exception as e:
        std_logger.error(f'Failed to get autoscaling groups of customer {customer.name}')
        std_logger.error(e)

def _get_cloudfront(customer):
    client = get_client(customer, 'cloudfront')

    try:
        distributions = client.list_distributions()
        std_logger.debug(distributions)

        _save_object(customer, cur_date, 'distributions', distributions)

        if 'Items' in distributions['DistributionList']:
            for distribution in distributions['DistributionList']['Items']:
                _save_object(customer, cur_date, 'distribution', distribution)
    except Exception as e:
        std_logger.error(f'Failed to get cloudfront distribution of customer {customer.name}')
        std_logger.error(e)

def _get_route53(customer):
    client = get_client(customer, 'route53')

    try:
        # TODO: limited to 100
        hosted_zones = client.list_hosted_zones()
        std_logger.debug(hosted_zones)

        _save_object(customer, cur_date, 'hosted_zones', hosted_zones)

        for hosted_zone in hosted_zones['HostedZones']:
            zone = client.get_hosted_zone(Id=hosted_zone['Id'])
            _save_object(customer, cur_date, 'hosted_zone', zone)

            rrset = client.list_resource_record_sets(HostedZoneId=hosted_zone['Id'])
            _save_object(customer, cur_date, 'rrset', rrset)
    except Exception as e:
        std_logger.error(f'Failed to get hosted zones of customer {customer.name}')
        std_logger.error(e)
    
def _save_object(customer, date, object_type, object_value):
    infra_object = Infrastructure(
        customer=customer,
        date=date,
        object_type=object_type,
        object_value=json.dumps(object_value, default=str)
    )
    infra_object.save()
