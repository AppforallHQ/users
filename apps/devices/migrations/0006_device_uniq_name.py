# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('devices', '0005_auto_20150927_1608'),
    ]

    operations = [
        migrations.AddField(
            model_name='device',
            name='uniq_name',
            field=models.UUIDField(default=uuid.uuid4),
        ),
    ]
