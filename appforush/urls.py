from django.conf.urls import patterns, include, url
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
admin.autodiscover()
from apps.users.forms import LoginForm

urlpatterns = patterns('',
    url(r'^panel/admin/', include(admin.site.urls)),
    url(r'^', include('apps.users.urls')),

    #Log IN & OUT
    url(r'^panel/login/$', 'django.contrib.auth.views.login', {"authentication_form" : LoginForm},name="login"),
    url(r'^panel/logout/$', 'django.contrib.auth.views.logout', {'next_page': '/'}, name="logout"),

    # Password reset
    url(r'^accounts/password_reset/$',
        'django.contrib.auth.views.password_reset',
        name='password_reset_request'
    ),
    (r'^accounts/password_reset/done/$',
        'django.contrib.auth.views.password_reset_done'
    ),
    url(r'^accounts/reset/(?P<uidb36>[-\w]+)/(?P<token>[-\w]+)/$',
        'django.contrib.auth.views.password_reset_confirm',
        name='password_reset_form'
    ),
    (r'^accounts/reset/done/$',
        'django.contrib.auth.views.password_reset_complete'
    ),

    #Change Password
    url(r'^accounts/change_password/$',
        'django.contrib.auth.views.password_change',
        name='password_change'),
    url(r'^accounts/change_password_done/$',
        'django.contrib.auth.views.password_change_done',
        name='password_change_done'),


    url(r'^', include('apps.devices.urls')),
    url(r'^panel/', include('apps.panel.urls')),
    url(r'^i/',include('apps.shortener.urls')),
    url(r'^panel/api/', include('apps.tokenapi.urls')),
    url(r'^panel/appbuy/', include('apps.appbuy.urls')),
    url(r'^panel/media/(?P<path>.*)$', 'django.views.static.serve', {
        'document_root': settings.MEDIA_ROOT,
    }),
)
