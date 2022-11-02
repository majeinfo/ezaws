import logging

# TODO: le pricing ici devrait servir à construire les JS/HTML ?
# TODO: le pricing devrait dépendre de la région ?

std_logger = logging.getLogger('pricing')

ec2_pricing = {
    'a1.medium'	: 0.0288,
    'a1.large'	: 0.0576,
    'a1.xlarge'	: 0.1152,
    'a1.2xlarge'	: 0.2304,
    'a1.4xlarge'	: 0.4608,
    't1.micro'	: 0.02,
    't2.nano'	: 0.0063,
    't2.micro'	: 0.013,
    't2.small'	: 0.025,
    't2.medium'	: 0.05,
    't2.large'	: 0.101,
    't2.xlarge'	: 0.202,
    't2.2xlarge'	: 0.404,
    't3.nano'	: 0.0057,
    't3.micro'	: 0.0114,
    't3.small'	: 0.0228,
    't3.medium'	: 0.0456,
    't3.large'	: 0.0912,
    't3.xlarge'	: 0.1824,
    't3.2xlarge'	: 0.3648,
    't3a.nano'	: 0.0051,
    't3a.micro'	: 0.0102,
    't3a.small'	: 0.0204,
    't3a.medium'	: 0.0408,
    't3a.large'	: 0.0816,
    't3a.xlarge'	: 0.1632,
    't3a.2xlarge'	: 0.3264,
    'm1.small'	: 0.047,
    'm1.medium'	: 0.095,
    'm1.large'	: 0.19,
    'm1.xlarge'	: 0.379,
    'm2.xlarge'	: 0.275,
    'm3.medium'	: 0.073,
    'm3.large'	: 0.146,
    'm3.xlarge'	: 0.293,
    'm3.2xlarge'	: 0.585,
    'm4.large'	: 0.111,
    'm4.xlarge'	: 0.222,
    'm4.2xlarge'	: 0.444,
    'm4.4xlarge'	: 0.888,
    'm4.10xlarge'	: 2.22,
    'm4.16xlarge'	: 3.552,
    'm5.large'	: 0.107,
    'm5.xlarge'	: 0.214,
    'm5.2xlarge'	: 0.428,
    'm5.4xlarge'	: 0.856,
    'm5.8xlarge'	: 1.712,
    'm5.12xlarge'	: 2.568,
    'm5.16xlarge'	: 3.424,
    'm5.24xlarge'	: 5.136,
    'm5.metal'	: 5.136,
    'm6i.large'	: 0.107,
    'm6i.xlarge': 0.214,
    'm6i.2xlarge': 0.428,
    'm6i.4xlarge': 0.856,
    'm6i.8xlarge': 1.712,
    'm6i.12xlarge': 2.568,
    'c1.medium'	: 0.148,
    'c1.xlarge'	: 0.592,
    'c4.large'	: 0.113,
    'c4.xlarge'	: 0.226,
    'c3.large'	: 0.12,
    'c3.xlarge'	: 0.239,
    'r3.large'	: 0.185,
    'r3.xlarge'	: 0.371,
    'r4.large'	: 0.148,
    'r4.xlarge'	: 0.296
}

elb_pricing = {
    'classic': {
        'by_hour': 0.028,
        'by_gib': 0.008,
    },
    'application': {
        'by_hour': 0.0252,
        'by_lcu': 0.008,
    },
    'network': {
        'by_hour': 0.0252,
        'by_lcu': 0.008,
    }
}

cache_pricing = {
    'm1.small': 0.036,      # wrong
    't2.micro'	: 0.018,
    't2.small'	: 0.036,
    't2.medium'	: 0.073,
    'm4.large'	: 0.172,
    'm4.xlarge'	: 0.343,
    'm4.2xlarge'	: 0.686,
    'm4.4xlarge'	: 1.373,
    'm4.10xlarge'	: 3.433,
    'm3.medium'	: 0.095,
    'm3.large'	: 0.200,
    'm3.xlarge'	: 0.400,
    'm3.2xlarge'	: 0.785,
    'r3.large'	: 0.254,
    'r3.xlarge'	: 0.507,
    'r3.2xlarge'	: 1.014,
    'r3.4xlarge'	: 2.028,
    'r3.8xlarge'	: 4.056,
    'r4.large'	: 0.254,
    'r4.xlarge'	: 0.507,
    'r4.2xlarge': 1.014,
    'r4.4xlarge': 2.028,
    'r48xlarge': 4.056,
    'r4.16xlarge': 8.112,
}

ebs_pricing = { # per zone
    'gp2' : {
        'per_gib': 0.11,
    },
    'io1': {
        'per_gib': 0.138,
        'per_prov': 0.072,
    },
    'st1': {
        'per_gib': 0.05,
    },
    'sc1': {
        'per_gib': 0.028,
    },
    'snapshot': {
        'per_gib': 0.05,
    },
    'standard': {
        'per_gib': 0.055,
        'per_million_ops': 0.055,
    }
}

ON_DEMAND = 'on_demand'
RESERVED = 'reserved'
SPOT = 'spot'

class PricingException(Exception):
    def __init__(self, msg, *args, **kwargs):
        super().__init__(msg)
        self.args = args
        self.kwargs = kwargs


class Pricing:
    def __init__(self, zone):
        self._zone = zone


    def get_EC2_cost_per_hour(self, inst_model, inst_type=ON_DEMAND):
        if inst_model not in ec2_pricing:
            std_logger.error("get_EC2_cost_per_hour: unknown model: %s" % (inst_model,))
            #raise PricingException("get_EC2_cost_per_hour: unknown model: %s" % (inst_model,))
            return 0

        return int(ec2_pricing[inst_model] * 24 * 31)


    def get_ELB_cost_per_hour(self, elb_type):
        if elb_type not in elb_pricing:
            std_logger.error("get_ELB_cost_per_hour: unknown elb_type: " % (elb_type,))
            #raise PricingException("get_ELB_cost_per_hour: unknown elb_type: " % (elb_type,))
            return 0

        return int(elb_pricing[elb_type]['by_hour'] * 24 * 31)


    def get_ELB_cost_per_GiB(self, elb_type):
        if elb_type not in elb_pricing:
            std_logger.error("get_ELB_cost_per_GiB: unknown elb_type: %s" % (elb_type,))
            #raise PricingException("get_ELB_cost_per_GiB: unknown elb_type: %s" % (elb_type,))
            return 0

        return int(elb_pricing[elb_type]['by_gib]'] * 24 * 31)


    def get_ElastiCache_cost_per_hour(self, cache_type):
        if cache_type not in cache_pricing:
            std_logger.error("get_ElastiCache_cost_per_hour: unknown cache_type: %s" % (cache_type,))
            #raise PricingException("get_ElastiCache_cost_per_hour: unknown cache_type: %s" % (cache_type,))
            return 0

        return int(cache_pricing[cache_type] * 24 * 31)


    def get_EBS_cost_per_month(self, ebs_size, ebs_type, iops_count=None):
        if ebs_type not in ebs_pricing:
            std_logger.error("get_EBS_cost_per_month: unknown ebs_type: %s" % (ebs_type,))
            #raise PricingException("get_EBS_cost_per_month: unknown ebs_type: %s" % (ebs_type,))
            return 0

        size_price = ebs_pricing[ebs_type]['per_gib'] * ebs_size
        if ebs_type == 'io1':
            size_price += ebs_pricing[ebs_type]['per_prov'] * iops_count

        return int(size_price)


    def get_EIP_cost_per_month(self):
        '''This is the cost if the EIP is not attached or attached to a non-running instance'''
        return int(0.005 * 24 * 31)


