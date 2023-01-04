from django.urls import path
from . import views, ajax, audit

urlpatterns = [
    path('', views.index, name='console'),
    path('ajax/get_customers', ajax.get_customers, name='get_customers'),
    path('ajax/get_instance_metrics/<cust_name>/<instance_id>', ajax.get_instance_metrics, name='get_instance_metrics'),
    path('ajax/get_vol_ops_metrics/<cust_name>/<volume_id>', ajax.get_vol_ops, name='get_vol_ops'),
    path('ajax/get_elb_reqcount_metrics/<cust_name>/<elb_type>/<elb_name>', ajax.get_elb_reqcount, name='get_elb_reqcount'),
    path('ajax/get_cache_metrics/<cust_name>/<cache_type>/<cache_name>', ajax.get_cache_metrics, name='get_cache_metrics'),
    path('ajax/get_s3_metrics/<cust_name>/<bucket_name>/<location>', ajax.get_s3_metrics, name='get_s3_metrics'),
    path('ajax/check_permission/<cust_name>/<perm>', ajax.check_permission, name='check_permission'),
    path('get_instances/<cust_name>', views.get_instances, name='get_instances'),
    path('get_amis/<cust_name>', views.get_amis, name='get_amis'),
    path('get_reserved_instances/<cust_name>', views.get_reserved_instances, name='get_reserved_instances'),
    path('get_volumes/<cust_name>', views.get_volumes, name='get_volumes'),
    path('get_snapshots/<cust_name>', views.get_snapshots, name='get_snapshots'),
    path('check_snapshots/<cust_name>', views.check_snapshots, name='check_snapshots'),
    path('get_elbs/<cust_name>', views.get_elbs, name='get_elbs'),
    path('get_elasticache/<cust_name>', views.get_elasticache, name='get_elasticache'),
    path('get_s3/<cust_name>', views.get_s3, name='get_s3'),
    path('get_cloudfront/<cust_name>', views.get_cloudfront, name='get_cloudfront'),
    path('audit/<cust_name>', audit.auditAction, name='audit_action'),
    path('view_audit_reports/<cust_name>', audit.viewAuditReportsAction, name='view_audit_reports_action'),
    path('view_audit_report/<cust_name>/<report_name>', audit.viewAuditReportAction, name='view_audit_report_action'),
    path('cron_audit/<cust_name>', audit.cronAuditAction, name='cron_audit_action'),
    path('cron_audit_all_customers', audit.cronAuditAllCustomersAction, name='cron_audit_all_customers_action'),
    path('goto_console/<cust_name>', views.goto_console, name='goto_console'),
]