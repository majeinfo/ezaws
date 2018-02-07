from django.utils.translation import ugettext as _
from django.shortcuts import render, redirect
from django.http import HttpResponse

def indexAction(request):
    return render(request, 'home.html')


