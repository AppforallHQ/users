# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import apps.devices.models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('devices', '0003_auto_20150420_1559'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='user',
            field=apps.devices.models._ForeignKey(to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='devicechallengetoken',
            name='device',
            field=apps.devices.models._ForeignKey(to='devices.Device'),
        ),
    ]
