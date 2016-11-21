# -*- coding: utf-8 -*-

from django.conf.urls import patterns, url

from apps.shortener import views

urlpatterns = patterns(
    '',
    url(r'^(?P<short_url>\w+)$',
        views.redirect,
        name='redirect_url'),
)

