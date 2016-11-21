import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from apps.users.models import User

#We use this hack currently so that we can use session-based registration
class _ForeignKey(models.ForeignKey):
    allow_unsaved_instance_assignment = True


class Device(models.Model):
    user = _ForeignKey(User)
    device_id  = models.CharField(null= True, blank=True, max_length=40)
    device_version  = models.CharField(null= True, blank=True, max_length=120)
    device_product  = models.CharField(null= True, blank=True, max_length=120)

    uniq_name = models.UUIDField(null=False, blank=False, default=uuid.uuid4)

    idfv = models.CharField(null=True, blank=True, max_length=40)
    aid = models.CharField(null=True, blank=True, max_length=40)
    uuid = models.UUIDField(null=True, blank=True, max_length=40)

    email = models.EmailField(_('device email'),
        help_text = _('device email'))
    has_credit = models.BooleanField(_('has credit'),
        help_text = _('can install application?'),default=False)
    registered_ipa = models.BooleanField(_('registered for IPA'),
        help_text = _('registered for IPA file'),default=False)

    class Meta:
        ordering = ('user', 'device_id',)

    def __unicode__(self):
        return "%s %s" % (self.device_product, self.device_id)

class DeviceChallengeToken(models.Model):
    device = _ForeignKey(Device)
    token = models.CharField(max_length=50, unique=True)
    is_used = models.BooleanField(default=False)
    
    def __unicode__(self):
        return "%s" % (self.token) 
