from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

class Customer(models.Model):
    name = models.CharField(max_length=32)
    access_key = models.CharField(max_length=64, default='')
    secret_key = models.CharField(max_length=64, default='')
    owner_id = models.CharField(max_length=32, default='')
    region = models.CharField(max_length=16, default='eu-west-1')
    timezone = models.CharField(max_length=32, default='UTC')
    console_url = models.CharField(max_length=200, default='')
    admins = models.ManyToManyField(User)
    aws_resource_tag_name = models.CharField(max_length=32, default='NAME')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = [ "name" ]


class Infrastructure(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    date = models.DateTimeField('collect date')
    object_type = models.CharField(max_length=64)
    object_value = models.TextField()

    class Meta:
        ordering = ["customer", "date", "object_type"]


class AuditEntry(models.Model):
    action = models.CharField(max_length=64)
    ip = models.GenericIPAddressField(null=True)
    username = models.CharField(max_length=256, null=True)

    def __str__(self):
        return '{0} - {1} - {2}'.format(self.action, self.username, self.ip)


@receiver(user_logged_in)
def user_logged_in_callback(sender, request, user, **kwargs):
    ip = request.META.get('REMOTE_ADDR')
    AuditEntry.objects.create(action='user_logged_in', ip=ip, username=user.username)


@receiver(user_logged_out)
def user_logged_out_callback(sender, request, user, **kwargs):
    ip = request.META.get('REMOTE_ADDR')
    AuditEntry.objects.create(action='user_logged_out', ip=ip, username=user.username)


@receiver(user_login_failed)
def user_login_failed_callback(sender, credentials, **kwargs):
    AuditEntry.objects.create(action='user_login_failed', username=credentials.get('username', None))


