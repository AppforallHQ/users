# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_auto_20150420_1636'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserPoints',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('period_points', models.IntegerField(default=0)),
                ('all_points', models.IntegerField(default=0)),
                ('user', models.OneToOneField(to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='UserReferral',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('referred_user', models.OneToOneField(related_name='referred', to=settings.AUTH_USER_MODEL)),
                ('referrer_user', models.ForeignKey(related_name='referrer', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
