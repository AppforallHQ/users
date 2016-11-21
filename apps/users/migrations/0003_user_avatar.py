# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import apps.users.models
import apps.users.storage


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_auto_20150218_1745'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='avatar',
            field=models.ImageField(storage=apps.users.storage.OverwriteStorage(), null=True, upload_to=apps.users.models.avatar_image_path, blank=True),
            preserve_default=True,
        ),
    ]
