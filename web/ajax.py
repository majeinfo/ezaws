from .log import *
from django.http import HttpResponse, Http404
from .models import Customer
import json

def get_customers(request):
    queryset = Customer.objects.all()
    names = []
    for q in queryset: names.append(q.name)
    return HttpResponse(json.dumps({'status': True, 'names': names}), content_type="application/json")
