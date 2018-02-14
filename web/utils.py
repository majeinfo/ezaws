import boto3
from django.contrib import messages
from .models import Customer
import aws.definitions as awsdef


def check_perm_message(request, cust_name):
    messages.info(request, 'You should check your Access Keys <a href="/auth/check_key/' + cust_name + '">here</a>',
                  extra_tags='save')


def get_customers():
    queryset = Customer.objects.all()
    names = []
    for q in queryset: names.append(q.name)
    return sorted(names)


def get_customer(cust_name):
    customer = Customer.objects.get(name=cust_name)
    return customer


def get_client(customer, resource_name):
    '''Create a boto Client to manage Client Resources'''
    client = boto3.client(
        resource_name,
        region_name=customer.region,
        aws_access_key_id=customer.access_key,
        aws_secret_access_key=customer.secret_key
    )

    return client


def get_session(customer):
    '''Create a boto session to query Customer's Resources'''
    session = boto3.session.Session(
        region_name=customer.region,
        aws_access_key_id=customer.access_key,
        aws_secret_access_key=customer.secret_key
    )

    return session


def get_cloudwatch(customer):
    '''Create a boto cloudwatch object to query Customer's Resources'''
    session = get_session(customer)
    return session.client('cloudwatch')


def get_elasticache(customer):
    '''Create a boto elasticache object to query Customer's Resources'''
    session = get_session(customer)
    return session.client('elasticache')


def get_instance_name(inst):
    # Extract the 'name' from tags
    if inst.tags:
         for tag in inst.tags:
              if tag['Key'] == 'Name':
                   return tag['Value']

    return None

def instance_is_running(inst):
    return inst.state['Name'] == awsdef.EC2_RUNNING
