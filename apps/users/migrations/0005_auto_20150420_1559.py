# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.auth.models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_giftdata'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='user',
            managers=[
                (b'objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.AlterField(
            model_name='giftdata',
            name='getter_email',
            field=models.EmailField(max_length=254),
        ),
        migrations.AlterField(
            model_name='giftdata',
            name='giver_email',
            field=models.EmailField(max_length=254),
        ),
        migrations.AlterField(
            model_name='newslettersubscriber',
            name='email',
            field=models.EmailField(max_length=254),
        ),
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(max_length=254, verbose_name='email address', blank=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='groups',
            field=models.ManyToManyField(related_query_name='user', related_name='user_set', to='auth.Group', blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', verbose_name='groups'),
        ),
        migrations.AlterField(
            model_name='user',
            name='id',
            field=models.OneToOneField(primary_key=True, serialize=False, to='users.UserEmail'),
        ),
        migrations.AlterField(
            model_name='user',
            name='last_login',
            field=models.DateTimeField(null=True, verbose_name='last login', blank=True),
        ),
        migrations.AlterField(
            model_name='useremail',
            name='email',
            field=models.EmailField(max_length=254),
        ),
    ]
