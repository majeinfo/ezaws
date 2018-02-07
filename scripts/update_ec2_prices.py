import sys
import json

#download_url = 'https://pricing.us-east-1.amazonaws.com/offers/v2.0/aws/AmazonEC2/current/index.json'
price_file = 'index.json'

def _get_region(region):
    return region


data = None
with open(price_file) as json_data:
    data = json.load(json_data)
    json_data.close()

if not data:
    print('JSON Data are empty', file=sys.stderr)
    exit(1)

products = data['products']
terms = data['terms']

# prices[region][instanceType][term] = price
prices = {}

for k in products:
    if products[k]['productFamily'] != 'Compute Instance':
        continue

    attrs = products[k]['attributes']
    if attrs['operatingSystem'] != 'Linux':
        continue

    region = _get_region(attrs['location'])
    prices[region] = { 'instanceType': attrs['instanceType'], 'terms': {} }
    sku = k

    ondemand = terms['OnDemand']
    if not sku in ondemand: continue
    key1 = list(ondemand[sku])[0]
    pricedim = ondemand[sku][key1]['priceDimensions']
    key2 = list(pricedim)[0]
    if 'per Linux' not in pricedim[key2]['description']: continue
    prices[region]['terms']['onDemand'] = pricedim[key2]['pricePerUnit']['USD'] * 24 * 31

print(prices)


