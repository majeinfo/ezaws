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
                break

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
    # S3 bucket
    # AS group
    # Launch configuration
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

        infra_object = Infrastructure(
            customer=customer,
            date=cur_date,
            object_type='instances',
            object_value=instances
        )
        infra_object.save()
    except Exception as e:
        print(f'Failed to get instances of customer {customer.name}')
        print(e)

def _get_security_groups(customer):
    client = get_client(customer, 'ec2')
    try:
        sec_groups = client.describe_security_groups()
        if verbosity >= VERBOSE:
            print(sec_groups)

        infra_object = Infrastructure(
            customer=customer,
            date=cur_date,
            object_type='security_groups',
            object_value=sec_groups
        )
        infra_object.save()
    except Exception as e:
        print(f'Failed to get security groups of customer {customer.name}')
        print(e)

def _get_iam_roles(customer):
    pass

def _get_volumes(customer):
    client = get_client(customer, 'ec2')
    try:
        volumes = client.describe_volumes()
        if verbosity >= VERBOSE:
            print(volumes)

        infra_object = Infrastructure(
            customer=customer,
            date=cur_date,
            object_type='volumes',
            object_value=volumes
        )
        infra_object.save()
    except Exception as e:
        print(f'Failed to get volumes of customer {customer.name}')
        print(e)

def _get_snapshots(customer):
    client = get_client(customer, 'ec2')
    try:
        snapshots = client.describe_snapshots()
        if verbosity >= VERBOSE:
            print(snapshots)

        infra_object = Infrastructure(
            customer=customer,
            date=cur_date,
            object_type='snapshots',
            object_value=snapshots
        )
        infra_object.save()
    except Exception as e:
        print(f'Failed to get snapshots of customer {customer.name}')
        print(e)

def _get_elbs(customer):
    client = get_client(customer, 'elb')
    try:
        elbs = client.describe_load_balancers()
        if verbosity >= VERBOSE:
            print(elbs)

        infra_object = Infrastructure(
            customer=customer,
            date=cur_date,
            object_type='elbs',
            object_value=elbs
        )
        infra_object.save()
    except Exception as e:
        print(f'Failed to get elbs of customer {customer.name}')
        print(e)

    client = get_client(customer, 'elbv2')
    try:
        elbs = client.describe_load_balancers()
        if verbosity >= VERBOSE:
            print(elbs)

        infra_object = Infrastructure(
            customer=customer,
            date=cur_date,
            object_type='elbv2s',
            object_value=elbs
        )
        infra_object.save()

        for elb in elbs['LoadBalancers']:
            attrs = client.describe_load_balancer_attributes(LoadBalancerArn=elb['LoadBalancerArn'])
            value = {'LoadBalancerArn': elb['LoadBalancerArn'], "Attributes": attrs}

            infra_object = Infrastructure(
                customer=customer,
                date=cur_date,
                object_type='elbv2_attrs',
                object_value=value
            )
            infra_object.save()

        for elb in elbs['LoadBalancers']:
            listeners = client.describe_listeners(LoadBalancerArn=elb['LoadBalancerArn'])

            infra_object = Infrastructure(
                customer=customer,
                date=cur_date,
                object_type='elbv2_listeners',
                object_value=listeners
            )
            infra_object.save()

        for listener in listeners['Listeners']:
            rules = client.describe_rules(ListenerArn=listener['ListenerArn'])
            value = {'ListenerArn': listener['ListenerArn'], "Rules": rules}

        infra_object = Infrastructure(
            customer=customer,
            date=cur_date,
            object_type='elbv2_rules',
            object_value=value
        )
        infra_object.save()

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

        infra_object = Infrastructure(
            customer=customer,
            date=cur_date,
            object_type='target_groups',
            object_value=target_groups
        )
        infra_object.save()
    except Exception as e:
        print(f'Failed to get target groups of customer {customer.name}')
        print(e)