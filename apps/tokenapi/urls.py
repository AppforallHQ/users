from django.conf.urls import patterns, url


urlpatterns = patterns('apps.tokenapi.views',
    url(r'^token/new.json$', 'token_new', name='api_token_new'),
    url(r'^token/get$', 'get_safe_token', name='get_safe_token'),
    url(r'^token/getuser$', 'token_to_username', name='token_to_username'),
    url(r'^token/(?P<token>.{24})/(?P<user>\d+).json$', 'token', name='api_token'),
)
