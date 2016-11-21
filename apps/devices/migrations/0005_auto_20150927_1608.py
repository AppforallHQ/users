# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('devices', '0004_auto_20150420_1636'),
    ]

    operations = [
        migrations.AddField(
            model_name='device',
            name='aid',
            field=models.CharField(max_length=40, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='device',
            name='idfv',
            field=models.CharField(max_length=40, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='device',
            name='uuid',
            field=models.UUIDField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='device',
            name='device_id',
            field=models.CharField(max_length=40, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='device',
            name='device_product',
            field=models.CharField(max_length=120, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='device',
            name='device_version',
            field=models.CharField(max_length=120, null=True, blank=True),
        ),
    ]
