from django.core.exceptions import PermissionDenied
from .models import User, Customer

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

        print(admin.username, request.user)
        if str(admin.username) == str(request.user):
            return func(request, *args, **kwargs)

        raise PermissionDenied

    _wrap.__doc__ = func.__doc__
    _wrap.__name__ = func.__name__
    return _wrap

