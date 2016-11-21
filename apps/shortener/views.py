import bitly_api
from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponsePermanentRedirect,HttpResponse
from apps.shortener.models import ShortUrl
from django.shortcuts import get_object_or_404
import string
import random
from django.core.urlresolvers import reverse

def id_generator(size=7, chars=string.ascii_lowercase + string.ascii_uppercase + string.digits):
            return ''.join(random.choice(chars) for _ in range(size))

def local_shorten_url(url):
    created = False
    obj = None
    while not created:
        short_url = id_generator()
        obj,created = ShortUrl.objects.get_or_create(short_url=short_url,defaults={'long_url':url})
    return 'http://PROJECT.ir%s' % reverse(redirect,kwargs={'short_url':obj.short_url})


def shorten_url(url):
    try:
        bit = bitly_api.Connection(access_token=settings.BITLY_ACCESS_TOKEN)
        res = bit.shorten(url)
        return res['url']
    except:
        return local_shorten_url(url)


def redirect(request, short_url):
    obj = get_object_or_404(ShortUrl,short_url=short_url)
    # Count
    obj.count += 1
    obj.save()
    response = HttpResponse("", status=302)
    response['Location'] = obj.long_url
    return response
