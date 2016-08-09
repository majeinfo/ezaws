from django.db import models

class Customer(models.Model):
    name = models.CharField(max_length=32)
    access_key = models.CharField(max_length=64)
    secret_key = models.CharField(max_length=64)
    owner_id = models.CharField(max_length=32, default='')
    region = models.CharField(max_length=16, default='eu-west-1')
    console_url = models.CharField(max_length=200, default='')

    class Meta:
        ordering = [ "name" ]