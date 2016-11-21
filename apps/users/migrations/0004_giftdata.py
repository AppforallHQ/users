# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_user_avatar'),
    ]

    operations = [
        migrations.CreateModel(
            name='GiftData',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('giver_name', models.CharField(max_length=40, verbose_name='giver name')),
                ('getter_name', models.CharField(max_length=40, verbose_name='getter name')),
                ('giver_email', models.EmailField(max_length=75)),
                ('getter_email', models.EmailField(max_length=75)),
                ('getter_id', models.ForeignKey(related_name='getter_id+', to='users.UserEmail')),
                ('giver_id', models.ForeignKey(related_name='giver_id+', to='users.UserEmail')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
