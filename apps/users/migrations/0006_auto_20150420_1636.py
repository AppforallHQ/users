# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import apps.users.models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_auto_20150420_1559'),
    ]

    operations = [
        migrations.AlterField(
            model_name='giftdata',
            name='getter_id',
            field=apps.users.models._ForeignKey(related_name='getter_id+', to='users.UserEmail'),
        ),
        migrations.AlterField(
            model_name='giftdata',
            name='giver_id',
            field=apps.users.models._ForeignKey(related_name='giver_id+', to='users.UserEmail'),
        ),
        migrations.AlterField(
            model_name='newslettersubscriber',
            name='user',
            field=apps.users.models._ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AlterField(
            model_name='resetpasswordtoken',
            name='user',
            field=apps.users.models._ForeignKey(to=settings.AUTH_USER_MODEL),
        ),
    ]
