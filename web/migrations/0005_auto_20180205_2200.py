# Generated by Django 2.0.1 on 2018-02-05 21:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0004_customer_admins'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='email',
            field=models.EmailField(default='', max_length=128),
        ),
        migrations.AddField(
            model_name='customer',
            name='timezone',
            field=models.CharField(default='UTC', max_length=32),
        ),
    ]
