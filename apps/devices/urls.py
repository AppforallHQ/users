from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^panel/apply_promo/', 'apps.devices.views.apply_promo_code'),
    url(r'^panel/pay/invoice/(?P<invoice_id>\d+)$', 'apps.devices.views.start_invoice_pay',name='start_invoice_pay'),
    url(r'^panel/pay/(?P<gateway>[^/]+)', 'apps.devices.views.start_pay',name='start_pay'),
    url(r'^panel/payment/$', 'apps.devices.views.payment_callback',name='payment_callback'),
    url(r'^panel/payment/gift/$', 'apps.devices.views.gift_callback',name='gift_callback'),
    
    url(r'^panel/analytics/(?P<user_id>\d+)', 'apps.devices.views.send_analytics',name='send_analytics'),
    
    url(r'^panel/plans\.json$', 'apps.devices.views.plans_json' , name='plans_list'),
    url(r'^panel/plans_all\.json$', 'apps.devices.views.plans_all_json' , name='plans_all_list'),
    url(r'^panel/dev/(?P<device_token>\w+)/req_new\.mobileconfig$', 'apps.devices.views.mobileconfig_static'),
    url(r'^panel/new/$', 'apps.devices.views.new', name='newDevice'),
    url(r'^panel/query_udid$', 'apps.devices.views.get_user_id_from_udid'),
    url(r'^panel/query_username$', 'apps.devices.views.get_user_id_from_username'),
    url(r'^panel/get_status$', 'apps.devices.views.get_user_status'),
    url(r'^panel/basic_user_status', 'apps.devices.views.basic_user_status'),
    url(r'^panel/invoice/(?P<invoiceId>.*)', 'apps.devices.views.invoice',
        name="invoice"),
    url(r'^email/(?P<device_id>.*)/(?P<plan>.*)/$',
        'apps.devices.views.email',
        name="email"),
    url(r'^status/(?P<deviceId>.*)/$', 'apps.devices.views.check_credit',
        name="checkCredit"),
    url(r'^panel/recorder.php$', 'apps.devices.views.receive_device_details',
        name="receiveDeviceDetails"),
    url(r'^panel/(?P<device_id>.*)/temp.*$',
        'apps.devices.views.receive_device_details_success',
        name="receiveDeviceDetailsSuccess"),
        
    url(r'^panel/hooks/post_download/$', 'apps.devices.views.download_post_action'),
    url(r'^panel/get_data/?$', 'apps.devices.views.get_serialized_data'),
    url(r'^panel/device/block_switch/?$', 'apps.devices.views.block_device_switch'),
    url(r'^panel/get_udid/?$', 'apps.devices.views.mobile_email_to_udid'),
    url(r'^panel/dluser/(?P<uuid>[0-9a-f-]{36})/?$', 'apps.devices.views.unique_download_ipa', name='unique_download_ipa'),
)
