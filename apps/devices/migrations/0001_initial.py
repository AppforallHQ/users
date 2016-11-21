# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Device',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('device_id', models.CharField(max_length=40, null=True)),
                ('device_version', models.CharField(max_length=120, null=True)),
                ('device_product', models.CharField(max_length=120, null=True)),
                ('email', models.EmailField(help_text='device email', max_length=75, verbose_name='device email')),
                ('has_credit', models.BooleanField(default=False, help_text='can install application?', verbose_name='has credit')),
                ('registered_ipa', models.BooleanField(default=False, help_text='registered for IPA file', verbose_name='registered for IPA')),
            ],
            options={
                'ordering': ('user', 'device_id'),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DeviceChallengeToken',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('token', models.CharField(unique=True, max_length=50)),
                ('is_used', models.BooleanField(default=False)),
                ('device', models.ForeignKey(to='devices.Device')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
