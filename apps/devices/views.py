# -*- coding: utf-8 -*-
import re
import hashlib
from itertools import chain
from pymongo import MongoClient

from django.http import HttpResponse, HttpResponseRedirect,HttpResponsePermanentRedirect, JsonResponse
from django.http import Http404
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Q
import json,pika,os
from .forms import NewForm
from .models import Device, DeviceChallengeToken
from apps.users.models import User,UserEmail, UserPoints, UserReferral
import requests
import tasks

from celery import task
from celery.task.schedules import crontab
from celery.decorators import periodic_task
from djcelery import celery
from celery import Celery
from requests.auth import HTTPBasicAuth
from apps.tokenapi.decorators import token_required

from django.template.loader import get_template
from django.core.urlresolvers import reverse
from django.core import serializers
from django.contrib.sites.models import Site
from django.contrib.auth import login

import analytics
import subprocess

from apps.tokenapi.views import gen_token
from django.conf import settings
from plistlib import readPlistFromString
from apps.panel import f5adapter as f5
from base64 import b64encode
import string
import random
import logging
import graypy
from apps.shortener.views import shorten_url
from apps.devices.utils import send_sms

################################################################
# Logging stuff to see what the fuck is wrong with segment     #
################################################################

LOGSTASH_GELF_HOST = 'localhost'
LOGSTASH_GELF_PORT = 12201

logger = logging.getLogger(__name__)
handler = graypy.GELFHandler(LOGSTASH_GELF_HOST, LOGSTASH_GELF_PORT)
logger.addHandler(handler)

def on_error(error, items):
    logger.error(error, extra=items)

analytics.debug = True
analytics.on_error = on_error
################################################################
#                          Mongo Setup                         #
################################################################
con = MongoClient("localhost", 27017)
applicationsdb = con["applicationsdb"]

################################################################
# Logging stuff to see what the fuck is wrong with segment     #
################################################################

generate_token = lambda N: ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(N))

TOKEN_LENGTH = 40

# Valid UDID re
UDID_RE = r'^([a-f0-9]{40}|x0{39})$'

def email_to_udid(email):
    """Get UDID from an Email address.
    """
    devices = Device.objects.filter(email=email)
    udid_list = []
    for device in devices:
        if device.device_id != None:
            udid_list.append(device.device_id)
    return udid_list

def mobile_to_udid(mobile):
    """Get UDID from an Phone number.
    """
    user = User.objects.filter(mobile_number=mobile)
    devices = Device.objects.filter(user=user)
    udid_list = []
    for device in devices:
        if device.device_id != None:
            udid_list.append(device.device_id)
    return udid_list

@token_required
def mobile_email_to_udid(request):
    """Get a mobile/email from a POST request and return a list of related UDIDs.
    """
    if request.user.is_authenticated() and request.user.is_superuser:
        mobile = request.POST.get("mobile", None)
        email = request.POST.get("email", None)
        if mobile:
            udid_list = mobile_to_udid(mobile)
            return HttpResponse(json.dumps(udid_list))
        elif email:
            udid_list = email_to_udid(email)
            return HttpResponse(json.dumps(udid_list))
        else:
            raise Http404
    raise PermissionDenied()

def get_device_data(request):
    """Get a udid (device_id) in a post reqest and return its related data from
    Device model
    """
    udid = request.POST.get("udid")
    if not udid:
        raise Http404
    # Find last specified user name for udid and the retrive device_object query
    # set to do serilization on it.
    device_object = Device.objects.filter(device_id=udid).reverse()[0]
    return [device_object]

def get_user_data(request):
    """Get a udid (device_id) in a post request and return its related data from
    User model
    """
    udid = request.POST.get("udid")
    if not udid:
        raise Http404
    user_id = Device.objects.filter(device_id=udid).reverse()[0].user
    user_object = User.objects.filter(username=user_id)
    return user_object

def get_f5_data(request):
    """Get a udid (device_id) in a post request and return its related data our from
    F5 service.
    """
    udid = request.POST.get("udid")
    if not udid:
        raise Http404
    uuid = Device.objects.filter(device_id=udid).reverse()[0].id
    f5_data = f5.device_details(request, uuid)
    return json.dumps({'invoice': f5_data[0], 'plan': f5_data[1], 'record': f5_data[2]})


@token_required
def get_serialized_data(request):
    """Get a udid (device_id) in a post request and return its related data from Device and User models plus f5.
    """
    if request.user.is_superuser:
        udid = request.POST.get("udid")
        if not udid:
            raise Http404
        device_data = get_device_data(request)
        user_data = get_user_data(request)
        f5_data = get_f5_data(request)
        data = list(chain(device_data, user_data))
        serialized_data = serializers.serialize('json', data)
        # F5 data is string and cannot be used in serialize function.
        # So I append it to seriailize json result when I want to response.
        return HttpResponse(serialized_data[:-1] + "," + f5_data + "]")
    raise PermissionDenied()

@token_required
def block_device_switch(request):
    """Get a udid (device_id) in a post request and call F5's block_device API by its related uuid.
    """
    if request.user.is_superuser:
        auth = HTTPBasicAuth(settings.FPAN['auth']['username'], settings.FPAN['auth']['password'])
        udid = request.POST.get("udid")
        if not udid:
            raise Http404
        uuid = Device.objects.get(device_id=udid).id
        res = requests.post('http://localhost:3000/fpan/api/v2/block_device_switch', headers=f5.get_api_header(), data={"device_id": uuid})
        return HttpResponse(res.content)
    raise PermissionDenied()

def get_user_id(pk):
    return UserEmail.objects.get(id=pk).user_id

def get_user_by_id(user_id):
    """Check if user_id exists in UserEmail object or no. if yes return it's User
    object
    """
    try:
        return User.objects.get(id__user_id=int(user_id))
    except:
        return None

def add_user_points(user_id, point):
    """Get a user_id and add points to it.
    """
    try:
        user_obj, c = UserPoints.objects.get_or_create(user=get_user_by_id(user_id))
        user_obj.add_point(point)
    except:
        print("User_id is not valid")


def get_plan_label(label):
    dic = {
        '1' : 'starter',
        '3' : 'plus',
        '6' : 'premium',
        '12' : 'max'
    }
    return dic[str(label)]

def get_device_status(request,device_id):
    import apps.panel.f5adapter as f5
    tup = f5.device_details(request,device_id)
    print tup
    try:
        data = {
            'status' : 'ok',
            'user_status': (1 if tup[2]['is_active'] else 2),
        }
        return data
    except:
        return {}


def get_device_details(user):
    dic = {}
    from apps.panel.views import get_idevice_from_internal_name
    for dev in user.device_set.all():
        if dev.device_product:
            key = get_idevice_from_internal_name(dev.device_product)
            newkey = key
            i = 1
            while newkey in dic:
                newkey = key + (" (%d)" % i)
                i+=1
            dic[newkey] = dev.id
    return dic


def send_userdownloadlink_analytics(user):
    userDownloadUrl = {}
    for (product,device_id) in get_device_details(user).items():
        udid = Device.objects.get(pk=device_id).device_id
        try:
            r = requests.get('https://USER_APP_DOWNLOAD_PREFIX?udid=%s' % udid,verify=False)
            js = r.json()
            userDownloadUrl[product] = js['link']
        except: pass        
    analytics.identify(user.id.user_id,{
        'userDownloadUrl' : userDownloadUrl
    })


def send_user_udid_analytics(user):
    udid_dict = {}
    for (product,device_id) in get_device_details(user).items():
        udid = Device.objects.get(pk=device_id).device_id
        udid_dict[product] = udid
    analytics.identify(user.id.user_id,{
        'UDID' : udid_dict
    })

def send_mobileconfig_analytics(user,request):
    mobileconfig = {}
    for device in user.device_set.all():
        try:
            token = DeviceChallengeToken.objects.filter(device=device).order_by('-id')[0].token
            url = reverse('apps.devices.views.mobileconfig_static', args=(token,))
            mobileconfig_url = request.build_absolute_uri(url)
            mobileconfig_url = mobileconfig_url.replace("http://","https://");
            mobileconfig["Device %d" % device.id] = mobileconfig_url            
        except Exception as e:
            print e
    analytics.identify(user.id.user_id,{
        'mobileConfigUrl' : mobileconfig
    })


def send_user_latestplan_analytics(user,request):
    latestPlan = {}
    for device in user.device_set.all():
        if device.device_id:
            import apps.panel.f5adapter as f5
            tup = f5.device_details(request,device.id)
            try:
                latestPlan[device.device_id] = get_plan_label(tup[2]['plan_label'])
            except:
                pass
    analytics.identify(user.id.user_id,{
        'latestPlan' : latestPlan
    })

def send_user_state_analytics(user,request):
    state_dict = {}
    state = {
        '1' : 'active',
        '2' : 'limited',
        '3' : 'blocked'
    }
    for (product,device_id) in get_device_details(user).items():
        device_data = get_device_status(request,device_id)
        try:
            state_dict[product] = state[str(device_data['user_status'])]
        except Exception as e:
            print e
    analytics.identify(user.id.user_id,{
        'state' : state_dict
    })


def send_analytics(request,user_id):
    user = User.objects.get(id__user_id=int(user_id))
    send_user_state_analytics(user,request)
    return HttpResponse("OK")


def plans_json(request):
    plans_url = settings.FPAN['host'] + settings.FPAN['urls']['plans']
    auth = (settings.FPAN['auth']['username'], settings.FPAN['auth']['password'])
    r = requests.get(plans_url, headers=f5.get_api_header(), verify=False)

    if r.status_code != 200:
        res = {"results": {"error": True}}
    else:
        res = r.json()

    return HttpResponse(json.dumps(res["results"]))


def plans_all_json(request):
    return HttpResponse(json.dumps(plans_all()))


def get_avatar(user):
    if user.avatar:
        # ex: http://www.PROJECT.ir/panel/media/avatars/5b548c24fb12dcde259a7b07c0bb1361
        avatar = "http://www.PROJECT.ir/panel/" + user.avatar.url
    else:
        user_hash = hashlib.md5(user.email.lower().encode('utf-8')).hexdigest()
        avatar = "http://www.gravatar.com/avatar/%s?d=identicon&s=120" % user_hash
    return avatar

def get_user_id_from_udid(request):
    udid = request.GET["udid"].lower()

    try:
        device = Device.objects.filter(device_id=udid).order_by("-id")[0]
    except IndexError:
        import string
        rot13 = string.maketrans(
            "ABCDEFGHIJKLMabcdefghijklmNOPQRSTUVWXYZnopqrstuvwxyz",
            "NOPQRSTUVWXYZnopqrstuvwxyzABCDEFGHIJKLMabcdefghijklm")

        udid = string.translate(str(udid), rot13)
        device = Device.objects.filter(device_id=udid).order_by("-id")[0]

    import apps.panel.f5adapter as f5
    tup = f5.device_details(request, device.id,activate=True)
    invoice = tup[0]
    record = tup[2]

    avatar = get_avatar(device.user)

    data = {
        'userID': str(device.user.id.user_id),
        'name': unicode(device.user.first_name),
        'email': device.user.email,
        'avatar': avatar,
        'expire_date': record['due_date'],
        'plan': invoice['plan'],
        'status': user_status_calculater(tup),
    }
    return HttpResponse(json.dumps(data), content_type="application/json")

def unspacify(string):
    return re.sub(r'[< >]', '', string)

def validate_basic_device(idfv, aid, uuid, device_name, req_hash):
    """Validate basic device id's based on a 4th hashed argument
    """
    data = "{}|{}|{}|{}_{}".format(idfv, aid,
                                   uuid, device_name,
                                   settings.REG_PAD_FOR_HASH)
    hashed_data = hashlib.sha512(data).hexdigest()

    if not hashed_data == unspacify(str(req_hash)):
        logger.warning("Wrong hash: {} not equal {}".format(hashed_data, req_hash))
    else:
        logger.info("True hash")

    return True

def get_or_create_basic_device(user, idfv, aid, uuid):
    """If device exists (considering one of three ids are equal to one in user's device set')
    Just update device data, otherwise add a new device
    """
    device = Device.objects.filter(Q(idfv=idfv) | Q(aid=aid) | Q(uuid=uuid), user=user)
    if device:
        device = device.order_by('-id')[0]
        device.idfv = idfv
        device.aid = aid
        device.uuid = uuid
        device.save()
    else:
        device, created = Device.objects.get_or_create(user=user, idfv=idfv, aid=aid,
                                                       uuid=uuid, email=user.email)

    return device

def basic_user_status(request):
    """Get user email and check it for basic access status
    user_status codes:
    1: useremail is verified
    4: useremail is not verified
    """
    user_id = request.POST.get('id', None)
    res = {'status': 'ok'}
    if user_id:
        user = get_object_or_404(User, id__user_id=user_id)
        res["user_status"] = 1 if user.email_verified else 4
    return JsonResponse(res)

def get_user_id_from_username(request):
    """ Get a username and return it's related data from users table.
    It's somehow equivalant to get_user_id_from_udid for basic users
    which doesn't have any device and udid.

    It's also generates a token for it and appends it's value to json response.
    """
    username = request.POST.get('username', None)
    password = request.POST.get('password', None)

    idfv = request.POST.get('idfv', None)
    aid = request.POST.get('aid', None)
    uuid = request.POST.get('uuid', None)
    dev = request.POST.get('dev', None)
    req_hash = request.POST.get('data', None)

    if not (username and password and aid and idfv and uuid) \
       or not validate_basic_device(idfv, aid, uuid, dev, req_hash):
        raise Http404

    user = get_object_or_404(User, username__iexact=username)
    device = get_or_create_basic_device(user, idfv, aid, uuid)

    token = requests.post('http://API/token/get', data={'username': username,
                                                                             'password': password,
                                                                             'device': device.pk})
    if token.status_code != 200 or not token.json()['success']:
        raise Http404

    token_data = token.json()

    data = {
        'userID': str(user.id.user_id),
        'name': unicode(user.first_name),
        'email': user.email,
        'avatar': get_avatar(user),
        'token': token_data['token'],
        'device': token_data['device'],
        'expire_date': None,
        'plan': -1,
        'status': 1,
    }

    return HttpResponse(json.dumps(data), content_type="application/json")


def user_status_calculater(tup):
    if tup[2]['is_active']:
        return 1
    elif tup[2]['status'] == 6:
        return 3
    return 2

def get_user_status(request):
    udid = request.GET["id"]
    print udid
    try:
        device = Device.objects.filter(device_id=udid).order_by("-id")[0]
    except IndexError:
        import string
        rot13 = string.maketrans(
            "ABCDEFGHIJKLMabcdefghijklmNOPQRSTUVWXYZnopqrstuvwxyz",
            "NOPQRSTUVWXYZnopqrstuvwxyzABCDEFGHIJKLMabcdefghijklm")

        udid = string.translate(str(udid), rot13)
        try:
            device = Device.objects.filter(device_id=udid).order_by("-id")[0]
        except:
            return HttpResponse(json.dumps({"status":"errro","message":"Access denied!"}))
    import apps.panel.f5adapter as f5
    tup = f5.device_details(request,device.id,activate=True)
    print tup
    try:
        data = {
            'status' : 'ok',
            'user_status': user_status_calculater(tup),
        }
        
        if data['user_status']==2:
            data['link'] = tup[0][u'invoice_payment_url'][u'mellat']
        return HttpResponse(json.dumps(data), content_type="application/json")
    except:
        return HttpResponse(json.dumps({"status":"errro","message":"Access denied!"}))



def mobileconfig_static(request, device_token):
    url = reverse('apps.devices.views.receive_device_details')
    
    tokens = DeviceChallengeToken.objects.filter(token=device_token)
    
    if tokens.count() < 1:
        raise Http404
    elif tokens[0].is_used:
        return render_to_response('mobileconfig_used.html', {})
    
    context = {
        'id': device_token,
        'endpoint_url': request.build_absolute_uri(url).replace("http://", "https://")
    }

    response = render_to_response(
        'emails/mobileconfig.txt',
        RequestContext(request, context),
        content_type='application/xml'
    )
    content = response.content
    proc = subprocess.Popen("openssl smime -sign -signer cert/public.crt -inkey cert/private.rsa -certfile cert/chain.crt -nodetach -outform der",stdin=subprocess.PIPE,stdout=subprocess.PIPE,shell=True)
    
    response = HttpResponse(proc.communicate(content)[0],content_type='application/x-apple-aspen-config; chatset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="%s"' % 'req_new.mobileconfig'

    return response

def process_promo(request, promo):
    """Get a invoice token and apply promo on it.
    """
    promourl = settings.FPAN['host'] + settings.FPAN['urls']['apply']
    payload = {
        'promo_code' : promo,
        'token' : request.session['token']
    }
    r = requests.post(promourl, data=payload, headers=f5.get_api_header(), verify=False)
    if r.status_code != 200:
        return None
    res = r.json()
    if 'success' in r.json():
        res = r.json()
        if request.user.is_authenticated():
            analytics.track(request.session['user_id'],'promo_code_enter',{
                "promo_code" : promo
            })
        else:
            analytics.track(request.session['user_id'],'promo_code_enter',{
                "promo_code" : promo
            })
        request.session["price"] = res["final_price"]
    return res


@csrf_exempt
def apply_promo_code(request):
    promo_code = request.POST.get("promo_code",None)
    if not request.session.get("token",None) \
       or request.session.get('referral_promo'): # Make sure user doesn't have a promo
        return HttpResponse(json.dumps({"error":True}))
    res = process_promo(request, promo_code.strip())
    if not res:
        return HttpResponse(json.dumps({'error': True}))
    return HttpResponse(json.dumps(res))


@csrf_exempt
def gift_create(request):    
    try:
        plan = request.POST["plan"]
        request.session["plan"] = plan
        from apps.panel.f5adapter import plan_details
        request.session["price"] = plan_details(request,plan)["price"]
        subscribeUrl = settings.FPAN['host'] + settings.FPAN['urls']['v2gift']
        auth = (settings.FPAN['auth']['username'], settings.FPAN['auth']['password'])
        form = request.session['giftform']
        payload = {
            'plan' : plan,
            'giver_id': form.instance.giver_id,
            'getter_id': form.instance.getter_id,
            'giver_email': form.instance.giver_email,
            'getter_email': form.instance.getter_email,
            'giver_name': form.instance.giver_name,
            'getter_name': form.instance.getter_name,
            'callback_url' : request.build_absolute_uri(reverse('gift_callback')),
            'callback_token' : request.session.session_key
            }
        r = requests.post(subscribeUrl, headers=f5.get_api_header(), data=payload, verify=False)
        res = r.json()
        if(res['success']):
            analytics.track(request.session['user_id'],'gift_choose_plan',{"plan": get_plan_label(res["label"])})
            request.session['plan_label'] = res["label"]
            request.session['token'] = res['token']
            del res['token']
            for bank in res['active_invoice_payment_url']:
                res['active_invoice_payment_url'][bank]=reverse('start_pay',kwargs={'gateway':bank})
            return HttpResponse(json.dumps(res))
    except:
        import sys
        print sys.exc_info()
        import traceback
        print traceback.format_exc()
    return HttpResponse(json.dumps({'error':True,'errors':u"خطا در مراحل ثبت درخواست پرداخت"}))


def gen_promo(promo_type, partner=None, campaign=None):
    """Generate a dict of promo_code requested from f5's API based on type
    """
    gen_promo_url = settings.FPAN['host'] + settings.FPAN['urls']['generate_promo']
    data = {'type': promo_type}
    if partner:
        data['partner'] = partner
    elif campaign:
        data['campaign'] = campaign

    r = requests.post(gen_promo_url,
                     data=data,
                     headers=f5.get_api_header())

    if r.status_code == 200 and 'error' not in r.json():
        promo = r.json()
    else:
        promo = None

    return promo


def add_device_for_user(request, form_initial, data):
    """ Get a request object, device form_initialization data and user data
    to make a device object for user and return proper bank gateway to pay.
    """
    form = NewForm(data or None, initial=form_initial)
    if form.is_valid():
        request.session['deviceform'] = form.instance
        request.session["plan"] = data["plan"]
        from apps.panel.f5adapter import plan_details
        request.session["price"] = plan_details(request,data["plan"])["price"]
        subscribeUrl = settings.FPAN['host'] + settings.FPAN['urls']['v2subscribe']
        auth = (settings.FPAN['auth']['username'], settings.FPAN['auth']['password'])
        payload = {
            'plan' : form.cleaned_data['plan'],
            'email': form.instance.email,
            'callback_url' : request.build_absolute_uri(reverse('payment_callback')),
            'callback_token' : request.session.session_key
            }
        r = requests.post(subscribeUrl, headers=f5.get_api_header(), data=payload, verify=False)
        try:
            res = r.json()
            if(res['success']):
                request.session['token'] = res['token']
                del res['token']

                if request.user.is_authenticated():
                    analytics.track(request.session['user_id'], 'choose_plan',{"plan": get_plan_label(res["label"])})
                else:
                    analytics.track(request.session['user_id'],'choose_plan',{"plan": get_plan_label(res["label"])})

                    # If user uses a referral link and the referredBy attribute is registered in our system
                    # give him discount if configured so in F5
                    referredBy = request.session.get('referredBy', None)
                    if referredBy:
                        # Generate new promo code if user haven't one yet
                        if request.session.get('referral_promo', None):
                            promo = request.session['referral_promo']
                        elif get_user_by_id(referredBy):
                            # In case user doesn't have referral_promo,
                            # Generate, apply and save it
                            referrer_name = get_user_by_id(referredBy).username
                            promo = gen_promo('referred', partner=referrer_name)
                        else:
                            promo = gen_promo('campaign', campaign=referredBy)

                        if promo:
                            request.session['referral_promo'] = promo
                            # Apply promo if any generated.
                            ppromo = process_promo(request, promo['code'])
                            if ppromo and 'success' in ppromo:
                                res['referral_promo'] = ppromo

                for bank in res['active_invoice_payment_url']:
                    res['active_invoice_payment_url'][bank]=reverse('start_pay',kwargs={'gateway':bank})
                return res
        except:
            import sys
            print sys.exc_info()
            import traceback
            print traceback.format_exc()
        return {'error':True,'errors':u"خطا در مراحل ثبت درخواست پرداخت"}
    else:
        return {'error': True, 'errors': dict(form.errors.items())}


@csrf_exempt
def new(request):
    print 'CREATE NEW'
    initial = {}
    data = {}
    if request.user.is_authenticated():
        request.session['user_id'] = get_user_id(request.session['_auth_user_id'])
        initial['user'] = request.user
        initial['email'] = request.user.email
        data['email'] = request.user.email
        data['plan'] = request.POST.get('plan', None)
        data['user'] = request.user
    elif request.session.get("userform",None):
        user = request.session['userform'].instance
        initial['user'] = user
        initial['email'] = user.username
        data['email'] = user.username
        data['plan'] = request.POST.get('plan', None)
        data['user'] = user
    elif request.session.get("giftform",None):
        return gift_create(request)
    else:
        return HttpResponse(json.dumps({'error': True, 'errors': {u"خطا" : u"پلن وارد شده صحیح نیست"}}))

    res = add_device_for_user(request, initial, data)
    return HttpResponse(json.dumps(res))


@csrf_exempt
def gift_start_payment(request,gateway):
    payurl = settings.FPAN['host'] + settings.FPAN['urls']['v2_gift_payment']
    auth = (settings.FPAN['auth']['username'], settings.FPAN['auth']['password'])
    payload = {
        'gateway' : gateway,
        'token' : request.session['token'],
    }
    r = requests.post(payurl, data=payload, headers=f5.get_api_header(), verify=False)
    analytics.track(request.session['giver_id'],'gift_start_payment',{
        "gateway" : gateway    
    })
    if r.status_code != 200:
        return HttpResponse(json.dumps({'error': True}))

    return HttpResponse(r.text,content_type="text/html")

@csrf_exempt
def start_pay(request,gateway):
    if not request.session.get("token",None):
        print "Error in Token"
        return HttpResponse(json.dumps({"error":True}))
    if 'invoice_id' in request.session:
        del request.session['invoice_id']
        request.session.save()
    
    if request.session.get('gift',False):
        return gift_start_payment(request,gateway)
    
    if request.user.is_authenticated():
        user_id = request.session['user_id']
    else:
        user_id = request.session['user_id']
    payurl = settings.FPAN['host'] + settings.FPAN['urls']['v2payment']
    auth = (settings.FPAN['auth']['username'], settings.FPAN['auth']['password'])
    payload = {
        'gateway' : gateway,
        'token' : request.session['token'],
        'user_id': user_id
    }
    r = requests.post(payurl, data=payload, headers=f5.get_api_header(), verify=False)
    analytics.track(user_id,'start_payment',{
        "gateway" : gateway    
    })
    if r.status_code != 200:
        return HttpResponse(json.dumps({'error': True}))

    return HttpResponse(r.text,content_type="text/html")


@login_required
@csrf_exempt
def start_invoice_pay(request,invoice_id):
    from apps.panel.views import welcome_device
    if request.method == "POST" and 'gateway' in request.POST:
        payurl = settings.FPAN['host'] + settings.FPAN['urls']['invoice_payment']
        auth = (settings.FPAN['auth']['username'], settings.FPAN['auth']['password'])
        callback_url = request.build_absolute_uri(reverse(welcome_device,kwargs={'invoice_id':invoice_id}))
        payload = {
            'gateway' : request.POST['gateway'],
            'user_id': request.session['user_id'],
            'invoice_id': invoice_id,
            'callback_url' : callback_url,
            'token' : request.session['token'],
        }
        print callback_url
        r = requests.post(payurl, data=payload, headers=f5.get_api_header(), verify=False)
       
        if r.status_code != 200:
            return HttpResponse(json.dumps({'error': True}))
        request.session["invoice_id"] = invoice_id
        return HttpResponse(r.text,content_type="text/html")
    else:
        try:
            request.session['user_id'] = get_user_id(request.session['_auth_user_id'])
            payurl = settings.FPAN['host'] + settings.FPAN['urls']['begin_invoice_payment']
            auth = (settings.FPAN['auth']['username'], settings.FPAN['auth']['password'])
            callback_url = request.build_absolute_uri(reverse(welcome_device,kwargs={'invoice_id':invoice_id}))
            payload = {
                'user_id': request.session['user_id'],
                'invoice_id': invoice_id,
            }
            r = requests.post(payurl, data=payload, headers=f5.get_api_header(), verify=False)
            js = r.json()
            request.session['token'] = js['token']
            f5_settings = f5.get_settings(request)
            payment_availablity = 'block' if 'OMGPAY_DISABLE_FOR_USERS' in f5_settings and f5_settings['OMGPAY_DISABLE_FOR_USERS'] == True else 'none'
            variables = dict(
                invoice = {
                    "invoice_url" : js['url'],
                    "plan_label" : js['label'],
                    "plan_amt" : js[u'plan_amount'],
                    "amount" : js[u'amount'],
                },
                payment_availablity=payment_availablity,
            )
            return render_to_response(
                'invoice_payment.html',
                RequestContext(request, variables)
            )
        except:
            raise Http404



@csrf_exempt
def gift_callback(request):
    try:
        from importlib import import_module
        engine = import_module(settings.SESSION_ENGINE)
        session = engine.SessionStore(request.POST.get("tokenback"))
        print session.items()
        print request.POST
        if not request.POST.get("token") or not session.get("token",None) or request.POST.get("token") != session.get("token",None):
            raise PermissionDenied()
        if "success" in request.POST and "invoice_id" in request.POST:
            invoice_id = request.POST['invoice_id']
            promo_code = request.POST['promo_code']
            sales_reference_id = request.POST['sales_reference_id']
            giver_id = session['giver_id']
            getter_id = session['getter_id']
            plan_label = session['plan_label']
            price = int(session['price'])
            plan_amount = int(request.POST['plan_amount'])
            discount = plan_amount - price
            getter_name = session['getter_name']

            
            gift = session['giftform'].save()
            
            session.clear()
            session['gift_invoice_id'] = invoice_id
            session['sales_reference_id'] = sales_reference_id
            session['plan_amount'] = plan_amount
            session['plan_label'] = plan_label
            session['price'] = price
            session['discount'] = discount
            session['getter_name'] = getter_name
            session.save()
        
            analytics.track(getter_id,'gift_getter',{
                'giver_name' : gift.giver_name,
                'getter_name' : gift.getter_name,
                'plan' : plan_label,
                'generated_promo_code' : promo_code
            })
            
            analytics.track(giver_id,'gift_giver',{
                'giver_name' : gift.giver_name,
                'getter_name' : gift.getter_name,
                'getter_mail' : gift.getter_email,
                'plan' : plan_label,
                'plan_amount' : plan_amount,
                'discount' : discount,
                'amount' :  price,
                'sales_reference_id' : sales_reference_id,
            })
            
            from apps.panel.views import gift_thanks
            return HttpResponse(json.dumps({"success":True,"redirect":request.build_absolute_uri(reverse(gift_thanks))}))
        else:
            analytics.track(session['user_id'],"gift_unsuccessful_payment",{
                "error_code" : request.POST["res_code"]
            })
            return HttpResponse(json.dumps({"success":True,"inner_error_page":True,"error_msg":"خطا در پرداخت","link":"http://www.PROJECT.ir"}))
        
    except:
        import sys
        print sys.exc_info()
        import traceback
        print traceback.format_exc()
    return HttpResponse(json.dumps({"error":True}))

@csrf_exempt
def payment_callback(request):
    try:
        from importlib import import_module
        engine = import_module(settings.SESSION_ENGINE)
        session = engine.SessionStore(request.POST.get("tokenback"))
        print session.items()
        print request.POST
        if not request.POST.get("token") or not session.get("token",None) or request.POST.get("token") != session.get("token",None):
            raise PermissionDenied()
        if "success" in request.POST and "invoice_id" in request.POST:
            invoice_id = request.POST['invoice_id']
            
            user_id = 0
            if "_auth_user_id" in session:
                user = User.objects.get(pk=session["_auth_user_id"])
                session['deviceform'].user = user
                session['deviceform'].save()
                dev_id = session['deviceform'].pk
                update_credit(request,{"activate":True},dev_id)
                user_id = user.id.user_id
                analytics.identify(user_id)
                if 'invoice_id' in session:
                    send_user_latestplan_analytics(user,request)
            else:
                session['userform'].save()
                session['deviceform'].user = session['userform'].instance
                session['deviceform'].save()
                dev_id = session['deviceform'].pk
                update_credit(request,{"activate":True},dev_id)
                user = session['userform'].instance
                user_id = user.id.user_id
                analytics.identify(user_id)

                if session.get('referredBy', None) and get_user_by_id(session['referredBy']):
                    # If user is referred by a user add 1 point for referrer
                    add_user_points(session['referredBy'], 1)
                    referred_obj = get_user_by_id(user_id)
                    referrer_obj = get_user_by_id(session['referredBy'])
                    UserReferral.objects.create(referred_user=referred_obj,
                                                referrer_user=referrer_obj).save()

                session.clear()
                
                session['_auth_user_backend'] = 'apps.users.backends.CaseInsensitiveModelBackend'
                session['_auth_user_id'] = user.pk
                session_auth_hash = ''
                if hasattr(user, 'get_session_auth_hash'):
                    session_auth_hash = user.get_session_auth_hash()
                session['_auth_user_hash'] = session_auth_hash
            
            session.save()
            
            analytics.identify(user_id,{
                "email": user.username,
                "firstName": user.first_name,
                "newsletter" : True,
            })
            
            analytics.track(get_user_id(session["_auth_user_id"]),"successful_payment",{
                "invoice_id" : invoice_id
            })

            return HttpResponse(json.dumps({"success":True,"user_id":user_id,"uuid":dev_id,"redirect":request.build_absolute_uri(reverse(invoice,kwargs={"invoiceId":invoice_id}))}))
        else:
            if "_auth_user_id" in session:
                analytics.track(get_user_id(session["_auth_user_id"]),"unsuccessful_payment",{
                    "error_code" : request.POST["res_code"]
                })
            else:
                analytics.track(session['user_id'],"unsuccessful_payment",{
                    "error_code" : request.POST["res_code"]
                })
            if "_auth_user_id" in session:
                return HttpResponse(json.dumps({"success":True,"redirect":"/panel/invoicefail/%s"%request.POST["res_code"]}))
            else:
                return HttpResponse(json.dumps({"success":True,"inner_error_page":True,"error_msg":"خطا در پرداخت","link":"http://www.PROJECT.ir"}))
        
    except:
        import sys
        print sys.exc_info()
        import traceback
        print traceback.format_exc()
    return HttpResponse(json.dumps({"error":True}))



def invoice(request, invoiceId=None):
    subscribeUrl = settings.FPAN['host'] + settings.FPAN['urls']['invoice'] + invoiceId
    auth = (settings.FPAN['auth']['username'], settings.FPAN['auth']['password'])
    r = requests.get(subscribeUrl, headers=f5.get_api_header(), verify=False)

    if r.status_code != 200:
        return HttpResponse("Failed to process your payment. Contact hi@PROJECT.ir")

    res = r.json()
    device = get_object_or_404(Device, pk=int(res['subscription']['uuid']))
    
    if device.user.id.user_id != get_user_id(request.session['_auth_user_id']):
        raise Http404
    token = generate_token(TOKEN_LENGTH)
    
    while DeviceChallengeToken.objects.filter(token=token).count() > 0:
        token = generate_token(TOKEN_LENGTH)
        
    DeviceChallengeToken.objects.create(device=device, token=token, is_used=False)

    url = reverse('apps.devices.views.mobileconfig_static', args=(token,))
    mobileconfig_url = request.build_absolute_uri(url)

    # Provice email along with identify traits to make customer.io happy
    analytics.identify(device.user.id.user_id, traits={
        "email": device.user.username
    })
    #HTTPS FOR VERIFIED MOBILECONFIG FILE
    mobileconfig_url = mobileconfig_url.replace("http://","https://");
    # Use {{create_account.mobileconf_url}} in customer.io email body
    send_mobileconfig_analytics(device.user,request)
    event = "create_account"
    if len(device.user.device_set.all()) > 1:
        event = "add_new_device"
    
    if device.user.allow_sms:
        short_url = shorten_url(mobileconfig_url)
        send_sms(device.user.mobile_number, short_url ,"activation.sms", device.user)
    
    analytics.track(device.user.id.user_id, event, {
        "mobileconf_url": mobileconfig_url,
        "email": device.user.username
    })
    analytics.track(device.user.id.user_id, 'sign_up_newsletter', {
        "email": device.user.username
    })
    return redirect("/panel/devices/welcome/%s" % invoiceId)

@csrf_exempt
def update_credit(request,res, deviceId):
    print 'UPDATE CREDIT'
    device = get_object_or_404(Device, pk=deviceId)

    if res['activate']:
        device.has_credit = True
        device.save()
        #tasks.register_device_to_make_ipa.delay(device.device_id, device.user.first_name)
    else:
        device.has_credit = False
        device.save()

    return HttpResponse(res)
    variables = {}
    return render_to_response(
        'devices/pay_success.html',
        variables)

def check_credit(request, deviceId):
    device = get_object_or_404(Device, device_id=deviceId)

    return HttpResponse(device.has_credit)

@csrf_exempt
def email(request, device_id, plan):
    print 'GET EMAIL TEXT'
    return HttpResponse('{"success": "true"}')
    device = get_object_or_404(Device, pk=device_id)
    template = request.param['template']
    variables = RequestContext( request, {
        'device': device,
        'plan'  : plan})

    return render_to_response(
        'email/' + template  + '.html',
        variables)

broker_url = settings.BROKER_URL
app = Celery(broker=broker_url)

@csrf_exempt
def receive_device_details(request):

    print repr(request)

    body = request.body
    body = body[body.find('<?xml version="1.0"'):body.find('</plist>')+8]

    pl = readPlistFromString(body)

    deviceRecordId = pl['CHALLENGE']
    if not deviceRecordId:
        raise PermissionDenied()
        
    challenge_obj = get_object_or_404(DeviceChallengeToken, token=deviceRecordId, is_used=False)

    deviceId = pl['UDID']

    device = challenge_obj.device
    device.device_id = deviceId
    device.device_version = pl['VERSION']
    device.device_product = pl['PRODUCT']
    device.save()
    
    print 'DEVICE', device, deviceId
    
    challenge_obj.is_used = True
    challenge_obj.save()
    
    
    res = app.send_task('appsign.udid_tasks.register_udid', args=[pl['UDID'], device.user.first_name], queue='udid')

    print pl

    analytics.identify(device.user.id.user_id, traits={
        "email": device.user.username
    })
    analytics.track(device.user.id.user_id, 'send_udid',{"udid":pl['UDID']})
    send_user_state_analytics(device.user,request)
    send_user_udid_analytics(device.user)
    send_user_latestplan_analytics(device.user,request)
    # See http://stackoverflow.com/questions/5781314/getting-a-device-udid-from-mobileconfig
    # Shold be like http://example.com/directory
    url = request.build_absolute_uri(reverse('receiveDeviceDetailsSuccess', kwargs={'device_id': deviceId})) #should I pass params?
    url += "?params=done"

    url = settings.REPO_SUCCESS
    # return redirect('receiveDeviceDetailsSuccess' , params)
    print "heading to %s" % url
    return HttpResponsePermanentRedirect(url)

def receive_device_details_success(request, device_id):
    variables = RequestContext( request, {
        'device': device_id})
    return render_to_response(
        'devices/new_success.html',
        variables)

"""
This is something like what Nginx sends to this:
request = "GET /download/548c3b3945ce7b2e43867e4c/546655b64679e3688e690c14/23q482r77oo866328405o5s083r2ps963841so31/data/program.ipa HTTP/1.1"
status = "OK"
"""
        
def download_post_action(request):
    status = request.GET.get('status', None)
    req = request.GET.get('request', None)
    
    if status != "OK" or not request:
        # did not complete in anyway
        return HttpResponse("")
        
    if re.search(r"k0{39}", req):
        # User downloaded basic PROJECT. For now we don't have a better way to
        # track. #More Info:
        # https://www..com/app/PROJECT/pivot/threads/NODYbH1UPBIGtimunefqNoNSK36
        from datetime import datetime
        with open("/app/users/basic_download.log", "a") as logfile:
            logfile.write(str(datetime.now()) + " Basic app downloaded.\n")

        return HttpResponse("")

    res = re.search(r"/download/(\w+)/(\w+)/(\w{40})/data/", req)
    
    if not res:
        return HttpResponse("")
        
    res = res.groups()
    udid = res[2].decode('rot13')
    
    try:
        device = Device.objects.filter(device_id=udid).order_by("-id")[0]
    except IndexError:
        raise Http404("Device Not Found")
    
    # import apps.panel.f5adapter as f5
    # tup = f5.device_details(request, device.id,activate=True)

    # Activate user email address 
    user = device.user
    user.email_verified = True
    user.save()
    
    
    analytics.identify(device.user.id.user_id)
    analytics.track(device.user.id.user_id, 'download_PROJECT')
    
    return HttpResponse("")

def unique_download_ipa(request, uuid):
    """Get a device uuid and redirect user to privateaf link
    """
    try:
        device = get_object_or_404(Device, uniq_name=uuid)
        dev_doc = applicationsdb.users.find_one({'udid': device.device_id})
    except:
        raise Http404

    itms_scheme = "itms-services://?action=download-manifest&url={}"
    response = HttpResponse("", status=302)
    try:
        response['Location'] = itms_scheme.format(dev_doc["privateaf"])
    except Exception as e:
        raise Exception("privateaf doesn't exist {}".format(e))
    return response

