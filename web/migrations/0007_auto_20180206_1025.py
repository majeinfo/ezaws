# Generated by Django 2.0.1 on 2018-02-06 09:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0006_remove_customer_email'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customer',
            name='access_key',
            field=models.CharField(default='', max_length=64),
        ),
        migrations.AlterField(
            model_name='customer',
            name='secret_key',
            field=models.CharField(default='', max_length=64),
        ),
    ]
