# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('devices', '0002_device_user'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='email',
            field=models.EmailField(help_text='device email', max_length=254, verbose_name='device email'),
        ),
    ]
