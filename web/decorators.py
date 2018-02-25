import logging
from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext as _
from django.shortcuts import redirect, reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from .models import User, Customer

std_logger = logging.getLogger('general')


def user_is_owner(func):
    def _wrap(request, *args, **kwargs):
        # From Customers get the list of Users and check the authentified User is in the list
        # ... or the authentified User is an administrator !
        if request.user.is_superuser:
            return func(request, *args, **kwargs)

        if 'cust_name' not in request.resolver_match.kwargs:
            return PermissionDenied

        cust_name = request.resolver_match.kwargs['cust_name']
        customer = Customer.objects.get(name=cust_name)
        try:
            admin = customer.admins.get()
        except:
            raise PermissionDenied

        if str(admin.username) == str(request.user):
            return func(request, *args, **kwargs)

        raise PermissionDenied

    _wrap.__doc__ = func.__doc__
    _wrap.__name__ = func.__name__
    return _wrap


def console_defined(func):
    def _wrap(request, *args, **kwargs):
        # Customer must have defined his Console URL
        if 'cust_name' not in request.resolver_match.kwargs:
            return PermissionDenied

        cust_name = request.resolver_match.kwargs['cust_name']
        customer = Customer.objects.get(name=cust_name)
        if customer.console_url:
            return func(request, *args, **kwargs)

        messages.error(request, _('Please set your Console URL in this Form :'))
        std_logger.info("User %s has not defined the Console URL" % cust_name)
        #raise PermissionDenied
        return HttpResponseRedirect('/auth/profile') #, args=args, kwargs=kwargs)

    _wrap.__doc__ = func.__doc__
    _wrap.__name__ = func.__name__
    return _wrap



def aws_creds_defined(func):
    def _wrap(request, *args, **kwargs):
        # Customer must have defined his AWS Credentials
        if 'cust_name' not in request.resolver_match.kwargs:
            return PermissionDenied

        cust_name = request.resolver_match.kwargs['cust_name']
        customer = Customer.objects.get(name=cust_name)
        if customer.access_key and customer.secret_key:
            return func(request, *args, **kwargs)

        messages.error(request, _('Please set your Access and/or Secret Key in this Form :'))
        std_logger.info("User %s has not defined the AWS Keys" % cust_name)
        #raise PermissionDenied
        return HttpResponseRedirect('/auth/profile') #, args=args, kwargs=kwargs)

    _wrap.__doc__ = func.__doc__
    _wrap.__name__ = func.__name__
    return _wrap


