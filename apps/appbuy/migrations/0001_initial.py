# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
from django.conf import settings
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BoughtApp',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('app_name', models.CharField(max_length=100)),
                ('itunes_id', models.IntegerField()),
                ('ir_fee', models.IntegerField()),
                ('us_fee', models.DecimalField(max_digits=6, decimal_places=2)),
                ('appstore_url', models.URLField()),
                ('icon_normal', models.URLField()),
                ('icon_large', models.URLField()),
                ('icon_huge', models.URLField()),
                ('buy_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('status', models.CharField(default=0, max_length=1, choices=[(b'0', b'OrderedApp'), (b'1', b'StartPayment'), (b'2', b'PaymentDone'), (b'3', b'PaymentFailed'), (b'4', b'StartProcess'), (b'5', b'ProcessFailed'), (b'6', b'ProcessSucceeded')])),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
