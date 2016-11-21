from django.conf.urls import patterns, url
from django.views.generic import RedirectView

urlpatterns = patterns('',
    url(r'^init/$', 'apps.appbuy.views.start_buy_App', name="buyApp"),
    url(r'^checkout/$', 'apps.appbuy.views.buy_app_checkout', name="AppCheckout"),
    url(r'^finish/$', 'apps.appbuy.views.buy_app_callback', name="finishAppPayment"),
    url(r'^thanks/$', 'apps.appbuy.views.buy_app_thanks', name="buyAppThanks"),
    url(r'^error/$', 'apps.appbuy.views.error', name="error"),
    url(r'^api/change_status/$', 'apps.appbuy.views.change_order_status_api', name="changeOrderStatus"),
    url(r'^api/app_list/$', 'apps.appbuy.views.users_app_list_api', name="usersAppList"),
    url(r'^api/app_check/$', 'apps.appbuy.views.users_app_check_api', name="usersAppCheck"),
    url(r'^api/last_PROJECT2/$', 'apps.appbuy.views.last_apple_id', name="usersLastAppleId"),
    url(r'^api/get_report/$','apps.appbuy.views.get_report',name="appbuyReport"),
)
