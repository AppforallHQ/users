# -*- coding: utf-8 -*-
import json

import redis
import requests
import analytics

from celery import Celery

from django.conf import settings
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.shortcuts import render_to_response
from django.core.validators import validate_email
from django.views.decorators.csrf import csrf_exempt

from apps.tokenapi.decorators import token_required
from django.core.exceptions import PermissionDenied

from .models import BoughtApp, BlackList, AccountBalance
from django.db.models import Sum

from apps.users.models import User
from apps.users.models import UserEmail
from apps.panel import f5adapter as f5
from dateutil import parser

# Setup Redis client
RedisClient = redis.StrictRedis(host=settings.REDIS_HOST,
                                port=settings.REDIS_PORT, db=settings.REDIS_DB)


# Setup celery
capp = Celery(__name__, broker=settings.APPBUY_BROKER_URL)

GenericInitUrl = settings.FPAN['host'] + settings.FPAN['urls']['generic_init']
GenericPayAPI = settings.FPAN['host'] + settings.FPAN['urls']['generic_pay']

ERRORS = {"AFAPI_NOT_RESPONDING":
          {"code": 2,
           "msg": "مشکلی در ارتباط با AppStore رخ داده است."},

          "CHANGE_PRICE":
          {"code": 3,
           "msg": "مشکلی در محاسبه قیمت ریالی رخ داده است."},

          "DATA_VALIDATION":
          {"code": 1,
           "msg": "داده‌های ارسالی نامعتبر است."},

          "GenericInitAPI":
          {"code": 4,
           "msg": "مشکلی در ارتباط با درگاه بانک رخ داده است."},

          "WRONG_ORDER_ID":
          {"code": 5,
           "msg": "متاسفانه شناسه سفارش جاری وجود ندارد."},

          "PAYMENT_FAILED":
          {"code": 6,
           "msg": "خطا در پرداخت بانکی"},

          "PERMISION_DENIED":
          {"code": 7,
           "msg": "مشکلی در شناسایی نشست رخ داده است."}}



def change_to_local_price(us_fee):
    """Get us dollar change price from redis and apply it on us_fee.
    """
    dollar_change = RedisClient.get('dollar_change')
    if not dollar_change:
       raise ValueError(ERRORS['CHANGE_PRICE'])

    Rial_fee = float(us_fee) * int(dollar_change)

    return int(Rial_fee)


def get_app_data(appid):
    """Get an appid and grab it's data using AFAPI API.
    """
    try:
        res = requests.get(settings.AFAPI_APPDATA, params={'appid': appid})
        result = res.json()
        if len(result) == 0:
            raise
    except:
        raise ValueError(ERRORS['AFAPI_NOT_RESPONDING'])

    return result


def get_us_fee(user_id, app_data):
    """If it's possbile get the price showed to user from Redis, if not, get it
    from appdata and set it in the Redis for 15 minutes.
    """
    app_id = app_data['itunes_id']
    us_fee = RedisClient.get(user_id + app_id)
    if not us_fee:  # In case AFAPI failed to set users app price.
        us_fee = app_data['original_price']
        RedisClient.set(user_id + app_id, us_fee, 60*15)

    return us_fee


def check_balance():
    try:
        balance_object = AccountBalance.objects.all()[0]
    except:
        # REPORT ERROR
        return False

    if balance_object.Balance < settings.APPBUY_LIMIT:
        result =  False
    elif balance_object.Balance < settings.BALANCE_TH:
        # REPORT
        result = True

    analytics.track('55345194', 'appbuy_balance', {
        'balance': balance_object.Balance
    })
    return result


@csrf_exempt
def start_buy_App(request):
    """ Setup session to buy App
    """

    # In case of service is not available is required :D
    try:
        if not check_balance():
            raise
    except:
        return render_to_response("appbuy_unavailable.html")

    if not request.session.session_key:
        request.session.flush()

    try:
        try:
            user_id = request.GET.get('userid', None)
            app_id = request.GET.get('appid', None)
            apple_id = request.GET.get('PROJECT2', None)

            validate_email(apple_id)
            user_email_obj = UserEmail.objects.filter(user_id=user_id)

            black_listed = BlackList.objects.get(itunes_id=appid)
            if not user_id or not app_id or black_listed:
                raise
        except:
            raise ValueError(ERRORS['DATA_VALIDATION'])

        user = User.objects.get(id=user_email_obj)
        app_data = get_app_data(app_id)
        us_fee = get_us_fee(user_id, app_data)
        ir_fee = change_to_local_price(us_fee)

        order_model = BoughtApp(user=user,
                                # Truncate application name to first 100 char
                                app_name=app_data['app_name'][:100],
                                itunes_id=app_id,
                                apple_id=apple_id,
                                ir_fee=ir_fee,
                                us_fee=us_fee,
                                appstore_url=app_data['appstore_url'],
                                icon_normal=app_data['icon_normal'],
                                icon_large=app_data['icon_large'],
                                icon_huge=app_data['icon_huge'])

        # Save order object:
        order_model.save()

        # Save order_id to session to have access to object in feature.
        request.session['ir_fee'] = ir_fee
        request.session['us_fee'] = us_fee
        request.session['user_id'] = user_id
        request.session['apple_id'] = apple_id
        request.session['order_id'] = order_model.id
        request.session['app_name'] = app_data['app_name']
        request.session['itunes_id'] = app_data['itunes_id']
        request.session['icon_huge'] = app_data['icon_huge']
        request.session['icon_large'] = app_data['icon_large']
        request.session['icon_normal'] = app_data['icon_normal']
        request.session['user_name'] = user.first_name + user.last_name

        request.session.set_expiry(0)
        request.session.save()

        # Initialize the invoice on F5
        callback_url = request.build_absolute_uri(reverse('finishAppPayment'))
        order_data = {'email': apple_id,
                      'amount': ir_fee,
                      'callback_url': callback_url,
                      'callback_token': request.session.session_key}

        try:
            res = requests.post(GenericInitUrl, headers=f5.get_api_header(),
                                data=order_data).json()
            if not res['success']:
                raise
        except:
            raise ValueError(ERRORS["GenericInitAPI"])

        # Set token so F5 is able to know us.
        request.session['token'] = res['token']
        request.session.set_expiry(0)
    except ValueError as error:
        request.session['error'] = error.args[0]
        error_url = request.build_absolute_uri(reverse("error"))
        return HttpResponseRedirect(error_url)

    analytics.track(user_id, 'start_buy_App', {
        'app_id': app_id,
        'apple_id': apple_id,
    })

    payment_url = request.build_absolute_uri(reverse("AppCheckout"))
    return HttpResponseRedirect(payment_url)


def change_order_status(order_id, new_status):
    order_object = BoughtApp.objects.get(id=order_id)
    order_object.status = int(new_status)
    order_object.save()


@token_required
@csrf_exempt
def change_order_status_api(request):
    """Provide an interface to change BoughtApp order object status.
    Since statuses which are not related to payment are (3 < x < 7)
    I prefer to not give this API ability statuses other than this.

    For more information you can look inside .models.py.
    """
    if request.user.is_authenticated() and request.user.is_superuser:
        order_id = request.POST.get('order_id', None)
        new_status = request.POST.get('status', None)
        valid_status = new_status in ['4', '5', '6']
        try:
            order_exists = get_object_or_404(BoughtApp, id=order_id)
            if not (order_id and new_status and valid_status and order_exists):
                raise

            change_order_status(order_id, new_status)

            return HttpResponse(json.dumps({'done': True}))
        except:
            return HttpResponse(json.dumps({'done': False}))

    raise PermissionDenied()


#@token_required
@csrf_exempt
def last_apple_id(request):
    """Get a user_id in POST request and return the last apple_id which user used.
    If user doesn't have any apple_id recorder, return users Email address.
    """
    user_id = request.POST.get('user_id', None)
    if user_id:
        try:
            last_buy = BoughtApp.objects.filter(user_id=user_id).order_by('-buy_date')[0]
            apple_id = last_buy.apple_id
        except:
            user_email_obj = get_object_or_404(UserEmail, user_id=user_id)
            apple_id = user_email_obj.email

        return HttpResponse(json.dumps({'apple_id': apple_id}))
    else:
        return HttpResponse(json.dumps({'error': True}))


# @token_required
@csrf_exempt
def users_app_list_api(request):
    """Get a user_id and return all apps user bought using this service.
    """
    user_id = request.GET.get('user_id', None)
    if user_id:
        user_email_obj = get_object_or_404(UserEmail, user_id=user_id)
        user_obj = get_object_or_404(User, id=user_email_obj)

        user_apps = BoughtApp.objects.filter(user=user_obj, status=6).order_by('-buy_date')
        response = []
        if len(user_apps) > 0:
            for app in user_apps:
                response.append({'appname': app.app_name,
                                 'itunes_id': app.itunes_id,
                                 'apple_id': app.apple_id,
                                 'appstore_url': app.appstore_url,
                                 'icon': app.icon_normal,
                                 'status': app.status, })
        return HttpResponse(json.dumps(response))
    else:
        return HttpResponse(json.dumps({'error': True}))


@token_required
@csrf_exempt
def users_app_check_api(request):
    """Check if a user_id bought an app (itunes_id) or not. If yes, return a list
    of apple_id's which user used to buy that app.
    """
    if request.user.is_authenticated() and request.user.is_superuser:
        user_id = request.POST.get('user_id', None)
        app_id = request.POST.get('app_id', None)
        if user_id and app_id:
            user_email_obj = get_object_or_404(UserEmail, user_id=user_id)
            user_obj = get_object_or_404(User, id=user_email_obj)
            bought = BoughtApp.objects.filter(user=user_obj, itunes_id=app_id)
            if len(bought) > 0:
                apple_ids = []
                for item in bought:
                    apple_ids.append(item.apple_id)
                return HttpResponse(json.dumps({'status': False, 'ids': apple_ids}))
            return HttpResponse(json.dumps({'status': True}))
        else:
            return HttpResponse(json.dumps({'error': True}))
    raise PermissionDenied()




@csrf_exempt
def buy_app_checkout(request):
    """ Send a user with session created in start_app_buy to pay the bill.
    F5 token is needed in session to get no errors.
    """
    user_id = request.session.get('user_id', None)
    if not user_id:
        return HttpResponse(json.dumps({'error': True}))

    gateway = 'mellat'
    request_data = {'gateway': gateway,
                    'token': request.session.get('token', None)}

    headers = f5.get_api_header()
    res = requests.post(GenericPayAPI, headers=headers, data=request_data)

    if res.status_code == 200:
        # Set order_status to 1 => StartPayment
        order_id = request.session['order_id']
        change_order_status(order_id, 1)

        analytics.track(user_id, 'buyapp_payment', {
            "gateway": gateway,
        })
        return HttpResponse(res)

    return HttpResponse(json.dumps({'error': True}))


@csrf_exempt
def buy_app_callback(request):
    """After finishing users payment, create BoughtApp object and return
    """
    try:
        from importlib import import_module
        engine = import_module(settings.SESSION_ENGINE)
        session = engine.SessionStore(request.POST.get('tokenback'))
        if not request.POST.get('token') or not session.get('token', None) or request.POST.get('token') != session.get('token', None):
            raise ValueError(ERRORS['PERMISION_DENIED'])

        order_id = session['order_id']
        user_id = session['user_id']
        app_name = session['app_name']

        if "success" not in request.POST:
            # Set order_status to 3 => PaymentFailed

            change_order_status(order_id, 3)

            session.clear()
            session['error'] = ERRORS['PAYMENT_FAILED']
            session.save()

            analytics.track(user_id, 'buyapp_payment_failed', {
                'order_id': str(order_id),
                'app_name': app_name
            })

            error_url = request.build_absolute_uri(reverse("error"))
            return HttpResponse(json.dumps({'success': False, 'redirect': error_url}))

        analytics.track(user_id, 'buyapp_payment_successful', {
            'order_id': str(order_id),
            'app_name': app_name,
            'revenue': session.get('ir_fee', None)
        })

        thanks = request.build_absolute_uri(reverse('buyAppThanks'))
        return HttpResponse(json.dumps({'success': True, 'redirect': thanks}))

    except ValueError as error:
        request.session['error'] = error.args[0]
        error_url = request.build_absolute_uri(reverse("error"))
        return HttpResponseRedirect(error_url)

def dec_balance(amount):
    balance = AccountBalance.objects.all()[0]
    balance.Balance -= amount
    balance.save()

@csrf_exempt
def buy_app_thanks(request):
    """Show the result page to the app!
    """
    try:
        order_id_exists = 'order_id' in request.session
        if not order_id_exists:
            raise ValueError(ERRORS['WRONG_ORDER_ID'])

        app_id = request.session['itunes_id']
        apple_id = request.session['apple_id']
        order_id = request.session['order_id']
        user_id = request.session['user_id']

        # Set order_status to 2 => PaymentDone
        change_order_status(order_id, 2)

        # # Add task to celery
        try:
            # Stringify all elements since celery task expect them too
            args = [str(i) for i in [order_id, app_id, user_id, apple_id]]
            capp.send_task('apple.tasks.gift_app', args=args)
            dec_balance(request.session['us_fee'])
        except:
            # TODO log (no celery task runned)
            pass

        request.session.flush()
    except ValueError as error:
        request.session['error'] = error.args[0]
        error_url = request.build_absolute_uri(reverse("error"))
        return HttpResponseRedirect(error_url)

    return render_to_response('appbuy_thanks.html', {'order_id': order_id})


@csrf_exempt
def error(request):
    """Show appropriate error message!
    """
    error = request.session['error']
    request.session.flush()

    return render_to_response('error.html', {'err_code': error['code'],
                                             'err_msg': error['msg']})


@token_required
@csrf_exempt
def get_report(request):
    if request.user.is_authenticated() and request.user.is_superuser:
        FROM_DATE = parser.parse(json.loads(request.POST['FROM_DATE']))
        TO_DATE = parser.parse(json.loads(request.POST['TO_DATE']))
        q = BoughtApp.objects.filter(status=6).filter(buy_date__gte=FROM_DATE,buy_date__lt=TO_DATE)
        count = q.count()
        us_fee = float(q.aggregate(Sum('us_fee'))['us_fee__sum'] or 0)
        ir_fee = int(q.aggregate(Sum('ir_fee'))['ir_fee__sum'] or 0) / 10
        return HttpResponse(json.dumps({'count' : count,'ir_fee':ir_fee,'us_fee':us_fee}))
    raise PermissionDenied()
