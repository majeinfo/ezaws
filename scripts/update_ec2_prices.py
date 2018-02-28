import sys
import json

#download_url = 'https://pricing.us-east-1.amazonaws.com/offers/v2.0/aws/AmazonEC2/current/index.json'
price_file = '../data/index.json'

def _get_region(region):
    return region


data = None
with open(price_file) as json_data:
    data = json.load(json_data)
    json_data.close()

if not data:
    print('JSON Data are empty', file=sys.stderr)
    exit(1)

restype = 'ec2'
pubdate = data['publicationDate']
products = data['products']
terms = data['terms']

prices = {}

for k, v in products.items():
    p_sku = k
    if v['productFamily'] != 'Compute Instance' and v['productFamily'] != 'Dedicated Host':
        continue
    attrs = v['attributes']
    loc = attrs['location']
    inst_type = attrs['instanceType']
    tenancy = attrs['tenancy']
    op_system = attrs['operatingSystem']
    #print(p_sku, loc, inst_type, tenancy, op_system)

    prices[p_sku] = {
        'loc': loc, 'inst_type': inst_type, 'tenancy': tenancy, 'os': op_system,
        'OnDemand': {}, 'Reserved': {},
    }

for p_sku, v in terms['OnDemand'].items():
    if p_sku not in prices:
        #print(p_sku, 'not in prices')
        continue

    for k2, v2 in v.items():
        # normally only one item
        term_code = v2['offerTermCode']
       
        for k3, v3 in v2['priceDimensions'].items():
            desc = v3['description']
            price = v3['pricePerUnit']['USD']

        if 'termAttributes' in v2:
            a_terms = v2['termAttributes']
        else:
            a_terms = None

        prices[p_sku]['OnDemand'][term_code] = {
           'descr': desc, 'price': price, 'terms': a_terms
        }

for p_sku, v in terms['Reserved'].items():
    if p_sku not in prices:
        #print(p_sku, 'not in prices')
        continue

    for k2, v2 in v.items():
        # normally only one item
        term_code = v2['offerTermCode']
       
        for k3, v3 in v2['priceDimensions'].items():
            desc = v3['description']
            price = v3['pricePerUnit']['USD']

        if 'termAttributes' in v2:
            a_terms = v2['termAttributes']
        else:
            a_terms = None

        prices[p_sku]['Reserved'][term_code] = {
           'descr': desc, 'price': price, 'terms': a_terms
        }


for k, v in prices.items():
    print(k, v)


