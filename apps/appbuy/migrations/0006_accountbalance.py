# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appbuy', '0005_blacklist'),
    ]

    operations = [
        migrations.CreateModel(
            name='AccountBalance',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('Balance', models.DecimalField(max_digits=6, decimal_places=2)),
            ],
        ),
    ]
