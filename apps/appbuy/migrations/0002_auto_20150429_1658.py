# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appbuy', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='boughtapp',
            name='apple_id',
            field=models.EmailField(default='old_bought_app@PROJECT.ir', max_length=254),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='boughtapp',
            name='status',
            field=models.CharField(default=0, max_length=1, choices=[(b'0', b'Ordered App'), (b'1', b'Start Payment'), (b'2', b'Payment Done'), (b'3', b'Payment Failed'), (b'4', b'Start Process'), (b'5', b'Process Failed'), (b'6', b'Process Succeeded'), (b'7', b'Canceled By User')]),
        ),
    ]
