# Generated by Django 2.0.1 on 2018-02-26 15:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0007_auto_20180206_1025'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='aws_resource_tag_name',
            field=models.CharField(default='NAME', max_length=32),
        ),
    ]