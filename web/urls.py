from django.conf.urls import url
from . import views, ajax

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^ajax/get_customers', ajax.get_customers, name='get_customers'),
    url(r'^ajax/get_instance_metrics/(?P<cust_name>[^/]+)/(?P<instance_id>.*)', ajax.get_instance_metrics, name='get_instance_metrics'),
    url(r'^get_instances/(?P<cust_name>.*)', views.get_instances, name='get_instances'),
    url(r'^get_snapshots/(?P<cust_name>.*)', views.get_snapshots, name='get_snapshots'),
    url(r'^check_snapshots/(?P<cust_name>.*)', views.check_snapshots, name='check_snapshots'),
    url(r'^goto_console/(?P<cust_name>.*)', views.goto_console, name='goto_console'),
]