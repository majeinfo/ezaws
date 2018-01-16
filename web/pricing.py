# TODO: le pricing ici devrait servir à construire les JS/HTML ?
# TODO: le pricing devrait dépendre de la région ?

ec2_pricing = {
	't1.micro'	: 0.02,
	't2.nano'	: 0.0063,
	't2.micro'	: 0.013,
	't2.small'	: 0.025,
	't2.medium'	: 0.05,
	't2.large'	: 0.101,
	't2.xlarge'	: 0.202,
	't2.2xlarge'	: 0.404,
	'm1.small'	: 0.047,
	'm1.medium'	: 0.095,
	'm1.large'	: 0.19,
	'm1.xlarge'	: 0.379,
	'm2.xlarge'	: 0.275,
	'm3.medium'	: 0.073,
	'm3.large'	: 0.146,
	'm3.xlarge'	: 0.293,
	'm3.2xlarge'	: 0.585,
	'm4.large'	: 0.119,
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
        'by_gio': 0.008,
    },
    'application': {
        'by_hour': 0.0252,
        'by_gio': 0.006,
    },
    'network': {
        'by_hour': 0.0252,
        'by_gio': 0.006,
    }
}
