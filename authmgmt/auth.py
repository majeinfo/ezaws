import os
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from .forms import LoginForm
from web.models import User, Customer

def loginAction(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        # if request.session.test_cookie_worked():
        #     request.session.delete_test_cookie()
        # else:
        #     return HttpResponse("Please enable cookies and try again.")

        if form.is_valid():
            n = form.cleaned_data['username']
            p = form.cleaned_data['password']
            user = authenticate(username=n, password=p, request=request)
            if user is not None:
                login(request, user)

                # Set the Customer name in Session
                customers = list(user.customer_set.filter(admins=user.id))
                if len(customers):
                    request.session['customer'] = customers[0].name
                    #print(request.session['customer'])

                return HttpResponseRedirect('/web')

    else:
        form = LoginForm()

    request.session.set_test_cookie()
    return render(request, 'login.html', { 'form': form })


def logoutAction(request):
    logout(request)
    return HttpResponseRedirect('/web')


def hookDeployAction(request):
    # Should be in another Controller - normally called by DockerHub as a hook
    #os.system('sudo -u ezaws /home/ezaws/restart.sh')
    os.system('/home/ezaws/restart.sh')
    return HttpResponse("OK")


