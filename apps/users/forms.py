# -*- coding: utf-8 -*-
import re
from django import forms
from django.utils.translation import ugettext, ugettext_lazy as _
from django.contrib.auth.hashers import identify_hasher
from django.utils.html import format_html, format_html_join
from django.forms.utils import flatatt
from django.template import loader
from django.contrib.auth.hashers import make_password
from .models import User,GiftData
from PROJECT.utilities import random_generate
from django.contrib.auth.forms import AuthenticationForm

class UserCreationForm(forms.ModelForm):
    """
    A form that creates a user, with no privileges, from the given username and
    password.
    """
    error_messages = {
        'duplicate_username': "این ایمیل قبلا استفاده شده است.",
        'password_mismatch': _("The two password fields didn't match."),
    }
    first_name = forms.CharField(label=u"نام",
        help_text=_("Required."))
    username = forms.EmailField(label=_("Email"),
        help_text=_("Required."))
    password = forms.CharField(label=_("Password"),
        widget=forms.PasswordInput)
    mobile_number = forms.CharField(label=u"شماره موبایل",
        help_text=_("Required."))

    class Meta:
        model = User
        fields = ("username", "first_name", "mobile_number","password","allow_sms")

    def clean_password(self):
        password = self.cleaned_data['password']
        if not re.match(r'^.{8,64}$',password):
            raise forms.ValidationError(u"رمز عبور حداقل باید ۸ کاراکتر داشته باشد")
        return make_password(password)

    def clean_mobile_number(self):
        mobile_number = self.cleaned_data["mobile_number"]

        if not re.match(r"^0?9\d{9}$", mobile_number):
            raise forms.ValidationError(u"نا معتبر است.")

        if mobile_number[0] != "0":
            mobile_number = "0" + mobile_number

        return mobile_number

    def clean_username(self):
        # Since User.username is unique, this check is redundant,
        # but it sets a nicer error message than the ORM. See #13147.
        username = self.cleaned_data["username"]
        try:
            User._default_manager.get(username__iexact=username)
        except User.DoesNotExist:
            return username.lower() # force lowering the username
        raise forms.ValidationError(self.error_messages['duplicate_username'])

    def save(self, commit=True):
        user = super(UserCreationForm, self).save(commit=False)
        user.password = self.cleaned_data["password"]
        user.email = user.username
        user.verify_code = random_generate()
        if commit:
            user.save()
        return user



class GiftForm(forms.ModelForm):

    giver_name = forms.CharField(label=u"نام شما",
        help_text=_("Required."))
    giver_email = forms.EmailField(label="ایمیل شما",
        help_text=_("Required."))
    getter_name = forms.CharField(label=u"نام هدیه گیرنده",
        help_text=_("Required."))
    getter_email = forms.EmailField(label="ایمیل هدیه گیرنده",
        help_text=_("Required."))
    

    class Meta:
        model = GiftData
        fields = ("giver_name", "giver_email", "getter_name","getter_email")

    def clean_giver_email(self):
        username = self.cleaned_data["giver_email"]
        return username.lower()
    
    def clean_getter_email(self):
        username = self.cleaned_data["getter_email"]
        return username.lower()

    def save(self, commit=True):
        gift = super(GiftForm, self).save(commit=False)
        if commit:
            gift.save()
        return gift



  
class LoginForm(AuthenticationForm):
    username = forms.CharField(label=_("Username"), max_length=254, 
                               widget=forms.TextInput(attrs={'class': 'HELLO'}))

