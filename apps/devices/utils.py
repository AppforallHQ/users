# -*- coding: utf-8 -*-

from django.conf import settings
import requests
import time


TEMPLATES = {
    'activation.sms' : u'''سلام
به اپفورال خوش‌آمدید
لینک فعال‌سازی
%s'''
    ,
    'ipa_link.sms' : u'''جهت نصب اپفورال لینک زیر را باز ‌کنید:
%s'''
    ,
}


def send_sms(mobile, link, template, user=None):
    for retry in range(3):
        try:
            params = {
                'to': mobile,
                'body': TEMPLATES[template] % link
            }
            if user:
                params['user_id'] = user.id.user_id
            requests.get(settings.SMS_URL,params=params)

            break
        except:
            import traceback
            traceback.print_exc()
            time.sleep(1)
            continue
    return
