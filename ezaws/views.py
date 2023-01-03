from django.utils.translation import gettext as _
from django.shortcuts import render, redirect
from django.http import HttpResponse
import web.utils as utils

def indexAction(request):
    names = utils.get_customers()
    context = { 'names': names }
    return render(request, 'home.html', context)


