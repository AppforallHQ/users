# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appbuy', '0002_auto_20150429_1658'),
    ]

    operations = [
        migrations.AlterField(
            model_name='boughtapp',
            name='icon_huge',
            field=models.URLField(null=True),
        ),
        migrations.AlterField(
            model_name='boughtapp',
            name='icon_large',
            field=models.URLField(null=True),
        ),
        migrations.AlterField(
            model_name='boughtapp',
            name='icon_normal',
            field=models.URLField(null=True),
        ),
    ]
