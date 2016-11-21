# -*- coding: utf-8 -*-

from django.db import transaction
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.forms import (AdminPasswordChangeForm)
from django.contrib.auth.models import Group
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.html import escape
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext, ugettext_lazy as _
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.contrib.admin import SimpleListFilter
from apps.devices.models import Device, DeviceChallengeToken

from .models import User, NewsletterSubscriber, UserPoints
from .forms import UserCreationForm
# from .forms import UserChangeForm

csrf_protect_m = method_decorator(csrf_protect)

def has_unregistered_device(obj):
    return Device.objects.filter(user=obj, device_id=None).count() > 0
has_unregistered_device.boolean = True
has_unregistered_device.short_description = 'Unreg'

class HasUnregisteredDeviceListFilter(SimpleListFilter):
    title = "has unregistered device"
    parameter_name = "unreg_device"
    
    def lookups(self, request, model_admin):
        return (
            ('1', _('Yes')),
            ('0', _('No')),
        )
        
    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(device_set__device_id=None)
        else:
            return queryset.exclude(device_set__device_id=None)

class InlineDeviceAdmin(admin.StackedInline):
    model = Device
    extra = 0
    
class UserPointInline(admin.TabularInline):
    model = UserPoints
    readonly_fields = ('period_points', 'all_points',)

class UserAdmin(admin.ModelAdmin):
    add_form_template = 'admin/auth/user/add_form.html'
    
    inlines = [
        InlineDeviceAdmin,
        UserPointInline, 
    ]
    
    change_user_password_template = None
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email', 'email_verified', 'mobile_number')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2')}
        ),
    )
    # form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    list_display = ('id', 'username', 'email', 'first_name', 'is_staff', 'email_verified', 'mobile_number',)
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups', 'email_verified',)
    search_fields = ('id__user_id', 'username', 'first_name', 'last_name', 'email', 'email_verified', 'mobile_number')
    ordering = ('id',)
    filter_horizontal = ('groups', 'user_permissions',)

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return super(UserAdmin, self).get_fieldsets(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        """
        Use special form during user creation
        """
        defaults = {}
        if obj is None:
            defaults.update({
                'form': self.add_form,
                'fields': admin.util.flatten_fieldsets(self.add_fieldsets),
            })
        defaults.update(kwargs)
        return super(UserAdmin, self).get_form(request, obj, **defaults)

    def get_urls(self):
        from django.conf.urls import patterns
        return patterns('',
            (r'^(\d+)/password/$',
             self.admin_site.admin_view(self.user_change_password))
        ) + super(UserAdmin, self).get_urls()

    def lookup_allowed(self, lookup, value):
        # See #20078: we don't want to allow any lookups involving passwords.
        if lookup.startswith('password'):
            return False
        return super(UserAdmin, self).lookup_allowed(lookup, value)

    @sensitive_post_parameters()
    @csrf_protect_m
    @transaction.atomic
    def add_view(self, request, form_url='', extra_context=None):
        # It's an error for a user to have add permission but NOT change
        # permission for users. If we allowed such users to add users, they
        # could create superusers, which would mean they would essentially have
        # the permission to change users. To avoid the problem entirely, we
        # disallow users from adding users if they don't have change
        # permission.
        if not self.has_change_permission(request):
            if self.has_add_permission(request) and settings.DEBUG:
                # Raise Http404 in debug mode so that the user gets a helpful
                # error message.
                raise Http404(
                    'Your user does not have the "Change user" permission. In '
                    'order to add users, Django requires that your user '
                    'account have both the "Add user" and "Change user" '
                    'permissions set.')
            raise PermissionDenied
        if extra_context is None:
            extra_context = {}
        username_field = self.model._meta.get_field(self.model.USERNAME_FIELD)
        defaults = {
            'auto_populated_fields': (),
            'username_help_text': username_field.help_text,
        }
        extra_context.update(defaults)
        return super(UserAdmin, self).add_view(request, form_url,
                                               extra_context)

    @sensitive_post_parameters()
    def user_change_password(self, request, id, form_url=''):
        if not self.has_change_permission(request):
            raise PermissionDenied
        user = get_object_or_404(self.queryset(request), pk=id)
        if request.method == 'POST':
            form = self.change_password_form(user, request.POST)
            if form.is_valid():
                form.save()
                msg = ugettext('Password changed successfully.')
                messages.success(request, msg)
                return HttpResponseRedirect('..')
        else:
            form = self.change_password_form(user)

        fieldsets = [(None, {'fields': list(form.base_fields)})]
        adminForm = admin.helpers.AdminForm(form, fieldsets, {})

        context = {
            'title': _('Change password: %s') % escape(user.get_username()),
            'adminForm': adminForm,
            'form_url': form_url,
            'form': form,
            'is_popup': '_popup' in request.REQUEST,
            'add': True,
            'change': False,
            'has_delete_permission': False,
            'has_change_permission': True,
            'has_absolute_url': False,
            'opts': self.model._meta,
            'original': user,
            'save_as': False,
            'show_save': True,
        }
        return TemplateResponse(request,
            self.change_user_password_template or
            'admin/auth/user/change_password.html',
            context, current_app=self.admin_site.name)

    def response_add(self, request, obj, post_url_continue=None):
        """
        Determines the HttpResponse for the add_view stage. It mostly defers to
        its superclass implementation but is customized because the User model
        has a slightly different workflow.
        """
        # We should allow further modification of the user just added i.e. the
        # 'Save' button should behave like the 'Save and continue editing'
        # button except in two scenarios:
        # * The user has pressed the 'Save and add another' button
        # * We are adding a user in a popup
        if '_addanother' not in request.POST and '_popup' not in request.POST:
            request.POST['_continue'] = 1
        return super(UserAdmin, self).response_add(request, obj,
                                                   post_url_continue)
                                                   
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('user', 'email', 'created_at',)

admin.site.register(User, UserAdmin)
admin.site.register(NewsletterSubscriber, NewsletterSubscriberAdmin)
