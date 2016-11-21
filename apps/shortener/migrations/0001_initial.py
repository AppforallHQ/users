# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ShortUrl',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('short_url', models.CharField(unique=True, max_length=32)),
                ('long_url', models.CharField(max_length=1024)),
            ],
        ),
        migrations.AlterIndexTogether(
            name='shorturl',
            index_together=set([('short_url',)]),
        ),
    ]
