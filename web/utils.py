import boto3


def get_client(customer, resource_name):
    '''Create a boto Client to manage Client Resources'''
    client = boto3.client(
        resource_name,
        region_name=customer.region,
        aws_access_key_id=customer.access_key,
        aws_secret_access_key=customer.secret_key)

    return client


def get_session(customer):
    '''Create a boto session to query Customer's Resources'''
    session = boto3.session.Session(
        region_name=customer.region,
        aws_access_key_id=customer.access_key,
        aws_secret_access_key=customer.secret_key)

    return session


def get_cloudwatch(customer):
    '''Create a boto cloudwatch object  to query Customer's Resources'''
    session = get_session(customer)
    return session.client('cloudwatch')
