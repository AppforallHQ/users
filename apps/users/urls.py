from django.conf.urls import patterns, url
from django.views.generic import RedirectView

urlpatterns = patterns('',
    url(r'^panel/user.js$', 'apps.users.views.user_js', name='jsUser'),
    url(r'^panel/email_ajax/$', 'apps.users.views.email_ajax', name='emailAjax'),
    url(r'^signup/$', 'apps.users.views.register', name='registerUser'),
    url(r'^panel/register/api/$', 'apps.users.views.register_api', name='User_register_api'),
    url(r'^panel/gift/$', 'apps.users.views.start_gift', name='giftUser'),
    url(r'^panel/reset/$', 'apps.users.views.reset', name='passwordReset'),
    url(r'^panel/reset/(?P<key>.*)', 'apps.users.views.reset_pass', name='password_reset_form'),
    url(r'^panel/register/activate/(?P<verify_code>.*)/$', 'apps.users.views.register_verify', name="registerVetify"),
    url(r'^panel/register/resend_activation/$', 'apps.users.views.resend_activation_email', name="resend_vetify_code"),
    url(r'^panel/newsletter/subscribe/$', 'apps.users.views.subscribe_newsletter'),
    url(r'^panel/newsletter/unsubscribe/$', 'apps.users.views.unsubscribe_newsletter'),
    url(r'^panel/chat/$','apps.users.views.load_chat'),
    url(r'^panel/device_chat/$','apps.users.views.redirect_device_chat'),
    url(r'^panel/get_points/$','apps.users.views.report_user_points'),
    url(r'^panel/reset_points/$','apps.users.views.reset_user_points'),
    url(r'^panel/invite/$','apps.users.views.invite_contact_list'),
    url(r'^panel/getid/$','apps.users.views.get_user_id'),
    url(r'^panel/sms_basic/$','apps.users.views.sms_basic_app'),
)
