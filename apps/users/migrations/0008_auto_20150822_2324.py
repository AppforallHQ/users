# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_userpoints_userreferral'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='userpoints',
            options={'verbose_name': 'User points', 'verbose_name_plural': 'User points'},
        ),
        migrations.AddField(
            model_name='user',
            name='allow_sms',
            field=models.BooleanField(default=False),
        ),
    ]
