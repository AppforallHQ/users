import hashlib

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, UserManager
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core import validators
from django.utils import timezone

#We use this hack currently so that we can use session-based registration
class _ForeignKey(models.ForeignKey):
    allow_unsaved_instance_assignment = True

from .storage import OverwriteStorage
class UserEmail(models.Model):
    user_id = models.IntegerField(null=False,unique=True)
    email = email = models.EmailField()
    class Meta:
        index_together = (('email',),)
        
    def __unicode__(self):
        return '{}'.format(self.user_id)

def avatar_image_path(instance, filename):
    """Upload_to handler that gets a file name and an instance and will change the
    file name to instances md5 hashed email address.
    """
    ext = filename.split('.')[1]
    return '/'.join(['avatars', str(hashlib.md5(instance.email.lower()).hexdigest())])

class User(AbstractBaseUser, PermissionsMixin):
    id = models.OneToOneField(UserEmail,primary_key=True)
    verify_code = models.CharField(_('verify code'), max_length=30,
        null = True,
        blank= True)
    email_verified = models.BooleanField(_('verified status'),
        default  = False,
        help_text= _('Activation email check.'))

    mobile_number = models.CharField(_('mobile number'), max_length=30)
    allow_sms = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    avatar = models.ImageField(upload_to=avatar_image_path, storage=OverwriteStorage(), blank=True, null=True)
    
    username = models.CharField(_('username'), max_length=254, unique=True,
        help_text=_('Required. 30 characters or fewer. Letters, digits and '
                    '@/./+/-/_ only.'),
        validators=[
            validators.RegexValidator(r"^\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$", _('Enter a valid username.'), 'invalid')
        ])
    first_name = models.CharField(_('first name'), max_length=30, blank=True)
    last_name = models.CharField(_('last name'), max_length=30, blank=True)
    email = models.EmailField(_('email address'), blank=True)
    is_staff = models.BooleanField(_('staff status'), default=False,
        help_text=_('Designates whether the user can log into this admin '
                    'site.'))
    is_active = models.BooleanField(_('active'), default=True,
        help_text=_('Designates whether this user should be treated as '
                    'active. Unselect this instead of deleting accounts.'))
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    
    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def get_full_name(self):
        """
        Returns the first_name plus the last_name, with a space in between.
        """
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        "Returns the short name for the user."
        return self.first_name

    def email_user(self, subject, message, from_email=None, **kwargs):
        """
        Sends an email to this User.
        """
        send_mail(subject, message, from_email, [self.email], **kwargs)


class GiftData(models.Model):
    giver_id = _ForeignKey(UserEmail,related_name = 'giver_id+')
    getter_id = _ForeignKey(UserEmail,related_name = 'getter_id+')
    created_at = models.DateTimeField(default=timezone.now)

    giver_name = models.CharField(_('giver name'), max_length=40)
    getter_name = models.CharField(_('getter name'), max_length=40)

    giver_email = models.EmailField()
    getter_email = models.EmailField()


class NewsletterSubscriber(models.Model):
    user = _ForeignKey(User, null=True, blank=True)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)


class ResetPasswordToken(models.Model):
    user = _ForeignKey(User)
    token = models.CharField(max_length=64)


class UserPoints(models.Model):
    """Object model to save user points
    """
    user = models.OneToOneField(User)
    period_points = models.IntegerField(default=0)
    all_points = models.IntegerField(default=0)

    class Meta:
        verbose_name = "User points"
        verbose_name_plural = "User points"

    def add_point(self, point):
        self.period_points += point
        self.all_points += point
        self.save()

    def reset_period(self):
        self.period_points = 0
        self.save()

    def report(self):
        return (self.period_points, self.all_points,)

class UserReferral(models.Model):
    """Object model to save user referral history
    """
    referred_user = models.OneToOneField(User, related_name="referred")
    referrer_user = models.ForeignKey(User, related_name="referrer")
