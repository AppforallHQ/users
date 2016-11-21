# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from pymongo import MongoClient
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.auth import login
from django.utils.translation import ugettext_lazy as _
from django.contrib.sites.models import get_current_site
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
import json,re,os
from .forms import UserCreationForm,GiftForm
from .models import User, NewsletterSubscriber,ResetPasswordToken,UserEmail,GiftData, UserPoints
from apps.devices.views import get_or_create_basic_device, validate_basic_device, get_avatar, add_device_for_user, plans_all
from apps.panel.views import parse_plans
import tasks
from django.core.context_processors import csrf
import analytics
from django.core.urlresolvers import reverse
import analytics
from django.core.signing import Signer
from django.contrib.auth.hashers import make_password
import random
import requests
import base64
import urllib
from django.conf import settings
from apps.tokenapi.decorators import token_required
import redis
from django.core import validators
from django.core.exceptions import PermissionDenied
from ratelimit.decorators import ratelimit
from apps.devices.utils import send_sms

# Setup Redis client
redis_client = redis.StrictRedis(host=settings.REDIS_HOST,
                                 port=settings.REDIS_PORT, db=settings.TOKEN_BACKEND)

appdb = MongoClient(settings.MONGODB_HOST,settings.MONGODB_PORT)['appdb']

def _registration_email_send(request, user):
    user_id = user.id.user_id
    analytics.identify(user_id, {
        "newsletter": True,
        "unsubscribed": False,
        "activated": True,
        "email": user.username,
        "fullName": user.first_name,
        "firstName": user.first_name,
    })
    analytics.track(user_id,"activation_email",{
        "activation_path": reverse(register_verify, kwargs={"verify_code": user.verify_code})
    })

def resend_activation_email(request):
    username = request.POST.get('username', None)
    user = get_object_or_404(User, username=username)

    if user.email_verified or not user.verify_code:
        return JsonResponse({"done": False})
    _registration_email_send(request, user)
    return JsonResponse({"done": True})

USER_ID_RANGE_S = 100
USER_ID_RANGE_E = 999


def get_or_create_user_id(email):
    global USER_ID_RANGE_S
    global USER_ID_RANGE_E
    if os.environ.get('DEVELOPMENT',False):
        USER_ID_RANGE_S = 50000
        USER_ID_RANGE_E = 99999
    try:
        uid = UserEmail.objects.filter(email__iexact=email)[0]
        return uid
    except:
        ret = random.randrange(USER_ID_RANGE_S,USER_ID_RANGE_E)
        while len(UserEmail.objects.filter(user_id=ret)) > 0:
            ret = random.randrange(USER_ID_RANGE_S,USER_ID_RANGE_E)
        obj = UserEmail(email=email,user_id=ret)
        obj.save()
        return obj


def base64UrlEncode(input):
    b64 = base64.b64encode(input)
    b64 = b64.replace('=','_')
    b64 = b64.replace('+','-')
    b64 = b64.replace('/',',')
    return b64

utf8_encode = lambda t: unicode(t).encode('utf-8')

def lz(text):
    return base64UrlEncode(utf8_encode(unicode(text)))

def load_chat(request):
    return HttpResponse("No chat!")


def redirect_device_chat(request):
    return HttpResponse("No Chat!")


@csrf_exempt
def start_gift(request):
    if not request.session.session_key:
        request.session.flush()

    form = GiftForm(request.POST or None)

    if form.is_valid():
        request.session['gift'] = True
        request.session['giftform'] = form
        request.session['giftform'].instance.giver_id = get_or_create_user_id(form.instance.giver_email)
        request.session['giftform'].instance.getter_id = get_or_create_user_id(form.instance.getter_email)
        request.session['giver_id'] = request.session['giftform'].instance.giver_id.user_id
        request.session['user_id'] = request.session['giver_id']
        request.session['getter_id'] = request.session['giftform'].instance.getter_id.user_id
        request.session['getter_name'] = request.session['giftform'].instance.getter_name
        request.session.set_expiry(0)
        request.session.save()

        analytics.identify(str(request.session['giver_id']),{
            "email": form.instance.giver_email,
            "firstName": form.instance.giver_name,
        })
        analytics.identify(str(request.session['getter_id']),{
            "email": form.instance.getter_email,
            "firstName": form.instance.getter_name,
        })
        analytics.track(str(request.session['giver_id']),"gift_fill_form",{
            "getter_name": form.instance.getter_name,
            "getter_email": form.instance.getter_email,
        })


        return HttpResponse(json.dumps({
            'success': True,
            'email': form.instance.giver_email,
            'firstName': form.instance.giver_name
        }))


    target_dict = [(form.fields[field].label, message) for field, message in form.errors.items()]

    #if request.is_ajax():
    return HttpResponseBadRequest(json.dumps(dict(target_dict)))


@csrf_exempt
def register(request):
    from django.shortcuts import redirect
    return redirect('https://PROJECT.ir')

    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse("panel_index"))
    if not request.POST:
        dl_data = requests.post('http://localhost:3000/getcounter')

        if dl_data.status_code != 200:
            dl_data = 10000
        else:
            dl_data = dl_data.json()["count"]

        plans_data = plans_all()
        variables = {'plan': '1', # request.GET.get('plan', None),
                     'referredBy': request.GET.get('referredBy', None),
                     'utm_campaign': request.GET.get('utm_campaign', None),
                     "plans_data": plans_data,
                     "dl_data": dl_data}
        return render_to_response('vitrine/register.html', variables)

    if not request.session.session_key:
        request.session.flush()
    username = request.POST['username']

    try:
        user = User.objects.get(username__iexact=username)
        if not user.device_set.exists():
            user.delete()
    except User.DoesNotExist:
        pass

    form = UserCreationForm(request.POST or None)
    if form.is_valid():
        email = form.instance.username
        first_name = form.instance.first_name
        mobile_number = form.instance.mobile_number
        plan = request.POST.get("plan", None)
        newsletter = True if request.POST.get("signup_newsletter", False) else False

        request.session['userform'] = form
        request.session['referredBy'] = request.POST.get('referredBy', None)
        request.session['userform'].instance.id = get_or_create_user_id(form.instance.username)
        request.session['user_id'] = request.session['userform'].instance.id.user_id
        request.session.set_expiry(0)
        request.session.save()

        print request.session['user_id']

        device_init = {'email': email, 'user': form.instance}
        device_data = {'email': email, 'user': form.instance, 'plan': plan}

        device = add_device_for_user(request, device_init, device_data)

        if not device.get('success', None) or device['success'] is not True:
            return JsonResponse(device)

        referredBy = request.POST.get('utm_campaign') or request.POST.get('referredBy') or 'direct'

        full_name = username.strip()
        name_list = full_name.split()
        analytics.identify(str(request.session['user_id']),{
            "email": email,
            "fullName": full_name,
            "firstName": name_list[1] if name_list[0] == 'ﺱیﺩ' else name_list[0],
            "referredBy": referredBy,
            "imported" : False,
            "wouldBeInterestedIn" : [],
            'newsletter': newsletter,
            'unsubscribed': not newsletter,
        })
        analytics.track(str(request.session['user_id']),"fill_personal_data",{
            "phoneNumber": mobile_number
        })
        return JsonResponse({
            'success': True,
            'email': email,
            'firstName': first_name,
            'label': device['label'],
            'active_invoice_payment_url': device['active_invoice_payment_url'],
            'promo' : device.get('referral_promo', None)
        })


    target_dict = [(unicode(form.fields[field].label), message) for field, message in form.errors.items()]

    #if request.is_ajax():
    return HttpResponseBadRequest(json.dumps(dict(target_dict)))

@csrf_exempt
def register_verify(request, verify_code):
    user = get_object_or_404(User, verify_code=verify_code)

    if user.email_verified:
        raise Http404
    else:
        user.email_verified = True
        user.verify_code = None
        user.save()

        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user);

        variables = RequestContext( request, {
            'user': user,
        })
        return render_to_response(
            'registration/register_activate.html',
            variables
        )

def get_basic_campaign():
    """Simple function to apply campaign.
    # TODO: make it easier to change.
    """
    if datetime.now() < datetime(2016, 12, 6):
        return {"1yearfree": datetime.now() + timedelta(365)}
    return {}

def register_api(request):
    form = UserCreationForm(request.POST, None)
    if not form.is_valid():
        res = {"messages": [(unicode(form.fields[field].label), message) for field, message in form.errors.items()],
               "error": True}
        return JsonResponse(res)

    idfv = request.POST.get('idfv', None)
    aid = request.POST.get('aid', None)
    uuid = request.POST.get('uuid', None)
    dev = request.POST.get('dev', None)
    hash_req = request.POST.get('data', None)

    if not (idfv and aid and uuid) or not validate_basic_device(idfv, aid, uuid, dev, hash_req):
        return JsonResponse({"error": True})

    form.instance.id = get_or_create_user_id(request.POST.get("username"))
    user = form.save()

    full_name = user.first_name.strip()
    name_list = full_name.split()
    analytics.identify(user.id.user_id,{
        "email": user.username,
        "fullName": full_name,
        "firstName": name_list[1] if name_list[0] == 'ﺱیﺩ' else name_list[0],
    })

    try:
        device = get_or_create_basic_device(user, idfv, aid, uuid)
    except:
        user.delete()
        return JsonResponse({"error": True})

    try:
        user_info_object = appdb.users.insert({
            'user_id': str(user.id.user_id),
            'device': str(device.pk),
            "campaigns": get_basic_campaign()
        })
    except:
        user.delete()
        device.delete()
        return JsonResponse({"error": True})

    _registration_email_send(request, user)
    return JsonResponse({"done": True})


@csrf_exempt
def reset_pass(request,key):
    try:
        print key
        (pk,token) = Signer().unsign(key).split("---")
        print pk,token
        pk = UserEmail.objects.get(user_id=int(pk)).id
        user = get_object_or_404(User,pk=pk)
        rtoken = get_object_or_404(ResetPasswordToken,user=user,token=token)

        # Clean all anonymous api token recores
        redis_client.delete(pk)

        pass_error = None
        pass_success=None
        from django import forms
        if request.method=="POST":
            try:
                challengetoken = request.POST["challengetoken"]
                new_pass = request.POST["new_password"]
                new_rpass = request.POST["new_rpassword"]
                if new_pass!=new_rpass:
                    pass_error="رمز های عبور وارد شده یکسان نیستند"
                    raise Exception()
                if not re.match(r'^.{8,64}$',new_pass):
                    raise forms.ValidationError(u"رمز عبور حداقل باید ۸ کاراکتر داشته باشد")

                user.password = make_password(new_pass)
                user.save()
                rtoken.delete()

                pass_success='''رمز عبور با موفقیت تغییر یافت<br/>
                برای ورود به <a href='/panel/login/'>اینجا</a> مراجعه کنید'''

            except forms.ValidationError:
                pass_error = "رمز عبور باید حداقل دارای ۸ کاراکتر باشد"
            except:
                if not pass_error:
                    pass_error = "اطلاعات وارد شده صحیح نیست"



        variables = RequestContext( request, {
            'view':'reset','pass_error':pass_error,'pass_success':pass_success,'token':key,
        })
        variables.update(csrf(request))
        return render_to_response(
            'registration/reset.html',
            variables
        )
    except Exception as e:
        print e
        raise Http404

@csrf_exempt
def reset(request):
    r_error,r_success = False,False
    if request.method == "POST":
        if 'challengetoken' in request.POST and 'new_password' in request.POST:
            return reset_pass(request,request.POST['challengetoken'])
        try:
            import uuid
            email = request.POST['username']
            user = User.objects.get(email__iexact=email)
            token = uuid.uuid4().hex
            mdl = ResetPasswordToken(user=user,token=token)
            mdl.save()
            key = Signer().sign(str(user.id.user_id)+"---"+token)
            analytics.identify(user.id.user_id, traits={
                'isActive': True,
                "email": user.email
            })
            url = request.build_absolute_uri(reverse(reset_pass,args=(key,)))
            print url
            analytics.track(user.id.user_id, 'password_reset', {
                "change_url": url,
                "email": user.email
            })
            r_success = True
        except:
            import sys
            print sys.exc_info()
            r_error = True
    variables = RequestContext( request, {
          'view':'email','r_error':r_error,'r_success':r_success,
        })
    variables.update(csrf(request))
    return render_to_response(
        'registration/reset.html',
        variables
    )

def user_js(request):
    user_data = {}

    if request.user.is_authenticated():
        user = request.user
        user_data = {
            'id': user.id.user_id,
            'firstName': user.first_name,
            'email': user.email,
            'loggedIn' : True,
            'avatar': get_avatar(user)
        }
    else:
        user_data = {
            'loggedIn': False,
        }

    response = "var user_data = {};".format(json.dumps(user_data))
    return HttpResponse(response, content_type='application/javascript')

def email_ajax(request):
    email = request.POST['email']
    try:
        user = User.objects.get(id__email__iexact=email)
    except User.DoesNotExist:
        return HttpResponse(json.dumps({
            'success': True
        }))
    return HttpResponse(json.dumps({
        'success': False
    }))

@csrf_exempt
def subscribe_newsletter(request):
    email = request.POST.get('email', None)

    if not email:
        response = {
            'error': True,
            'status': 'BadRequest'
        }
        return HttpResponseBadRequest(json.dumps(response), content_type="application/json")
    else:
        email = email.lower()
    try:
        validators.validate_email(email)
    except:
        response = {
            'error': True,
            'status': 'BadRequest'
        }
        return HttpResponseBadRequest(json.dumps(response), content_type="application/json")
    if NewsletterSubscriber.objects.filter(email=email).count() > 0:
        response = {
            'error': False,
            'status': 'AlreadySubscribed'
        }
        return HttpResponse(json.dumps(response), content_type="application/json")

    subscriber = NewsletterSubscriber()

    useremail = get_or_create_user_id(email)
    analytics.identify(useremail.user_id, traits={
        'email': email,
        'newsletter': True,
        'unsubscribed': False,
    })


    subscriber.email = email
    analytics.track(useremail.user_id, 'subscribed_newsletter', {
        'email': email,
    })

    subscriber.save()

    response = {
        'error': False,
        'status': 'Subscribed'
    }
    return HttpResponse(json.dumps(response), content_type="application/json")

def unsubscribe_newsletter(request):
    email = request.GET.get('email', None)

    if not email:
        return HttpResponseBadRequest("")
    else:
        email = email.lower()

    subscriber = None

    try:
        subscriber = NewsletterSubscriber.objects.get(email=email)
        subscriber.delete()
        useremail = get_or_create_user_id(email)
        analytics.identify(useremail.user_id, traits={
            'newsletter': False,
            'unsubscribed': True,
        })
        analytics.track(useremail.user_id, 'unsubscribed_newsletter', {
            'email': email,
        })
    except:
        pass # Let's handle the unsubscription if even we don't have the user!


    return render_to_response("unsubscribed.html", {}, content_type="application/json")


@token_required
def report_user_points(request):
    if request.user.is_authenticated() and request.user.is_superuser:
        user_id = request.POST.get('user_id', None)

        try:
            points_obj, c = UserPoints.objects.get_or_create(user__id__user_id=int(user_id))

            return HttpResponse(json.dumps({'period_points': points_obj.period_points,
                                        'all_points': points_obj.all_points}))
        except:
            return HttpResponse(json.dumps({'error': 'user has no points'}))

    raise PermissionDenied()

@token_required
def reset_user_points(request):
    if request.user.is_authenticated() and request.user.is_superuser:
        user_id = request.POST.get('user_id', None)

        try:
            points_obj, c = UserPoints.objects.get_or_create(user__id__user_id=int(user_id))
            points_obj.reset_period()

            return HttpResponse(json.dumps({'done': True}))
        except:
            return HttpResponse(json.dumps({'error': 'wrong user_id'}))
    raise PermissionDenied()

@login_required
def invite_contact_list(request):
    """Get a list of contact items {'name': Shahin, 'email': ishahinism@gmail.com}
    and trigger invitation email from inviter user.
    """
    contacts = request.POST.get('contacts', None)
    result = {}
    try:
        contacts = json.loads(contacts)
        inviter = request.user
        inviter_id = request.user.id.user_id
        inviter_name = inviter.first_name + inviter.last_name
        for item in contacts:
            email = item['email']
            name = item['name']
            user_id = get_or_create_user_id(email).user_id

            analytics.identify(str(user_id),{
                "email": email,
                "firstName": name,
            })

            data = {
                'name': name,
                'inviter': str(inviter),
                'inviter_id': inviter_id,
                'inviter_name': inviter_name,
            }

            analytics.track(user_id, 'invited', data)
        result['done'] = True
    except:
        result['error'] = 'Invalid data'

    return HttpResponse(json.dumps(result))


@token_required
def get_user_id(request):
    """Get an email address and return it's user_id
    """
    email = request.POST.get("email", None)
    response = {}
    if email:
        try:
            validators.validate_email(email)
            response = {"id": get_or_create_user_id(email).user_id}
            analytics.identify(str(response), {"email": email})
        except:
            pass
    return HttpResponse(json.dumps(response))

def get_user_ip(request):
    if 'HTTP_X_FORWARDED_FOR' in request.META:
        ip = request.META['HTTP_X_FORWARDED_FOR'].split(",")[0].strip()
    else:
        ip = request.META['REMOTE_ADDR']
    return ip

def sms_basic_app(request):
    """A view to sms basic app link for user
    """
    mobile = request.POST.get("mobile", None)
    userip = get_user_ip(request)

    if not mobile or not re.match(r'09[0-9]{9}', mobile):
        return JsonResponse({'error': True})

    user_attampts = int(redis_client.get(userip) or 0)
    if user_attampts >= 3:
        return JsonResponse({'error': True})

    redis_client.setex(userip, 24 * 60 * 60, user_attampts + 1)

    send_sms(mobile , settings.AFABASIC_DL_LINK, "ipa_link.sms")
    return JsonResponse({"done": True})
