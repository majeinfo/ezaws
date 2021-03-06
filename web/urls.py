from django.conf.urls import url
from . import views, ajax, audit

urlpatterns = [
    url(r'^$', views.index, name='console'),
    url(r'^ajax/get_customers', ajax.get_customers, name='get_customers'),
    url(r'^ajax/get_instance_metrics/(?P<cust_name>[^/]+)/(?P<instance_id>.*)', ajax.get_instance_metrics, name='get_instance_metrics'),
    url(r'^ajax/get_vol_ops_metrics/(?P<cust_name>[^/]+)/(?P<volume_id>.*)', ajax.get_vol_ops, name='get_vol_ops'),
    url(r'^ajax/get_elb_reqcount_metrics/(?P<cust_name>[^/]+)/(?P<elb_type>[^/]+)/(?P<elb_name>.+)', ajax.get_elb_reqcount, name='get_elb_reqcount'),
    url(r'^ajax/get_cache_metrics/(?P<cust_name>[^/]+)/(?P<cache_type>[^/]+)/(?P<cache_name>.+)', ajax.get_cache_metrics, name='get_cache_metrics'),
    url(r'^ajax/get_s3_metrics/(?P<cust_name>[^/]+)/(?P<bucket_name>[^/]+)', ajax.get_s3_metrics, name='get_s3_metrics'),
    url(r'^ajax/check_permission/(?P<cust_name>[^/]+)/(?P<perm>.*)', ajax.check_permission, name='check_permission'),
    url(r'^get_instances/(?P<cust_name>[^/]+)', views.get_instances, name='get_instances'),
    url(r'^get_amis/(?P<cust_name>.*)', views.get_amis, name='get_amis'),
    url(r'^get_reserved_instances/(?P<cust_name>.*)', views.get_reserved_instances, name='get_reserved_instances'),
    url(r'^get_volumes/(?P<cust_name>.*)', views.get_volumes, name='get_volumes'),
    url(r'^get_snapshots/(?P<cust_name>.*)', views.get_snapshots, name='get_snapshots'),
    url(r'^check_snapshots/(?P<cust_name>.*)', views.check_snapshots, name='check_snapshots'),
    url(r'^get_elbs/(?P<cust_name>.*)', views.get_elbs, name='get_elbs'),
    url(r'^get_elasticache/(?P<cust_name>.*)', views.get_elasticache, name='get_elasticache'),
    url(r'^get_s3/(?P<cust_name>.*)', views.get_s3, name='get_s3'),
    url(r'^audit/(?P<cust_name>.*)', audit.auditAction, name='audit_action'),
    url(r'^view_audit_reports/(?P<cust_name>.*)', audit.viewAuditReportsAction, name='view_audit_reports_action'),
    url(r'^view_audit_report/(?P<cust_name>[^/]+)/(?P<report_name>[^/]+)', audit.viewAuditReportAction, name='view_audit_report_action'),
    url(r'^cron_audit/(?P<cust_name>.*)', audit.cronAuditAction, name='cron_audit_action'),
    url(r'^cron_audit_all_customers', audit.cronAuditAllCustomersAction, name='cron_audit_all_customers_action'),
    url(r'^goto_console/(?P<cust_name>.*)', views.goto_console, name='goto_console'),
]