# -*- coding: utf-8 -*-
import uuid

from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.users.models import User

ORDER_STATUS = (
    ('0', 'اپلیکیشن سفارش داده‌شده'),
    ('1', 'شروع مرحله‌ی پرداخت'),
    ('2', 'پرداخت موفقیت‌آمیز'),
    ('3', 'خطا در انجام پرداخت'),
    ('4', 'شروع عملیات'),
    ('5', 'خطا در عملیات'),
    ('6', 'عملیات موفقیت‌آمیز'),
    ('7', 'لغو شده توسط کاربر')
)

def validate_only_one_instance(obj):
    model = obj.__class__
    if model.objects.count() > 0 and obj.id != model.objects.get().id:
        raise ValidationError("You can only create one {} instance".format(model.__name__))

# Create your models here.
class BoughtApp(models.Model):
    """A model to save list of application that users bought from appstore.
    """
    # Unique random id
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User)
    app_name = models.CharField(max_length=100)
    itunes_id = models.IntegerField()  # Appid
    apple_id = models.EmailField()     # Users Appleid
    ir_fee = models.IntegerField()     # Rials
    us_fee = models.DecimalField(max_digits=6, decimal_places=2)  # dollars

    appstore_url = models.URLField()
    icon_normal = models.URLField(null=True)
    icon_large = models.URLField(null=True)
    icon_huge = models.URLField(null=True)

    buy_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=1, default=0, choices=ORDER_STATUS)

    def __unicode__(self):
        return self.app_name

    def get_status(self):
        return ORDER_STATUS[int(self.status)][1]

class BlackList(models.Model):
    """ A model to hold black listed app.
    """
    itunes_id = models.IntegerField(null=False, blank=False, unique=True)  # Appid
    description = models.TextField(null=False, blank=False)
    date = models.DateTimeField(default=timezone.now)

class AccountBalance(models.Model):
    """ A simple model to hold current balance.
    """
    Balance = models.DecimalField(max_digits=6, decimal_places=2)  # dollars

    def clean(self):
        validate_only_one_instance(self)
