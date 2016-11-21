# -*- coding: utf-8 -*-
import operator
import re
from django.contrib.auth.decorators import login_required

from django.http import HttpResponse,HttpRequest,Http404, HttpResponseRedirect
from django.core.exceptions import PermissionDenied
from functools import wraps
import json
from django.shortcuts import render_to_response
from django.template import RequestContext
from apps.devices.models import Device, DeviceChallengeToken
from apps.users.models import User, UserReferral, UserPoints
from django.core.urlresolvers import reverse
from django.utils import formats
from apps.panel import f5adapter as f5
from apps.devices.views import plans_json
import requests
import dateutil.parser
from django.core.context_processors import csrf
import jdatetime
from django.conf import settings
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from apps.tokenapi.decorators import token_required
import analytics
from copy import deepcopy
from django.utils import timezone
from pymongo import MongoClient
import redis

from .forms import AvatarUpload

@login_required
def index(request):
    return HttpResponse("Hello, world")

# Setup Redis client
redis_client = redis.StrictRedis(host=settings.REDIS_HOST,
                                 port=settings.REDIS_PORT, db=settings.TOKEN_BACKEND)

# Mongo setup
mongo = MongoClient(settings.MONGODB_HOST, settings.MONGODB_PORT)
appdb = mongo['appdb']

IDEVICE_DICTIONARY = {
    'AppleTV2,1' : 'Apple TV 2G',
    'AppleTV3,1' : 'Apple TV 3G',
    'AppleTV3,2' : 'Apple TV 3G',
    
    'iPad1,1' : 'iPad',
    'iPad2,1' : 'iPad 2',
    'iPad2,2' : 'iPad 2',
    'iPad2,3' : 'iPad 2',
    'iPad2,4' : 'iPad 2',
    'iPad3,1' : 'iPad 3',
    'iPad3,2' : 'iPad 3',
    'iPad3,3' : 'iPad 3',
    'iPad3,4' : 'iPad 4',
    'iPad3,5' : 'iPad 4',
    'iPad3,6' : 'iPad 4',
    'iPad4,1' : 'iPad Air',
    'iPad4,2' : 'iPad Air',
    'iPad4,3' : 'iPad Air',
    'iPad5,3' : 'iPad Air 2',
    'iPad5,4' : 'iPad Air 2',
    
    'iPad2,5' : 'iPad mini 1G',
    'iPad2,6' : 'iPad mini 1G',
    'iPad2,7' : 'iPad mini 1G',
    'iPad4,4' : 'iPad mini 2',
    'iPad4,5' : 'iPad mini 2',
    'iPad4,6' : 'iPad mini 2',
    'iPad4,7' : 'iPad mini 3',
    'iPad4,8' : 'iPad mini 3',
    'iPad4,9' : 'iPad mini 3',
    
    'iPhone1,1' : 'iPhone',
    'iPhone1,2' : 'iPhone 3G',
    'iPhone2,1' : 'iPhone 3GS',
    'iPhone3,1' : 'iPhone 4',
    'iPhone3,2' : 'iPhone 4',
    'iPhone3,3' : 'iPhone 4',
    'iPhone4,1' : 'iPhone 4S',
    'iPhone5,1' : 'iPhone 5',
    'iPhone5,2' : 'iPhone 5',
    'iPhone5,3' : 'iPhone 5c',
    'iPhone5,4' : 'iPhone 5c',
    'iPhone6,1' : 'iPhone 5s',
    'iPhone6,2' : 'iPhone 5s',
    'iPhone7,2' : 'iPhone 6',
    'iPhone7,1' : 'iPhone 6 Plus',
}


def get_idevice_from_internal_name(name):
    d = {key.lower(): value for (key, value) in IDEVICE_DICTIONARY.items()}
    if name.lower().rstrip() in d:
        return d[name.lower().rstrip()]
    return name



################THIS PART IS USED FOR f5/cron/job.py
@token_required
def get_product_name(request):
    if request.user.is_superuser:
        try:
            device = request.POST.get("id")
            dev = Device.objects.get(pk=int(device))
            if not dev.device_id:
                return HttpResponse(json.dumps({"success":True,"product":"-"}))
            return HttpResponse(json.dumps({"success":True,"product":get_idevice_from_internal_name(dev.device_product)}))
        except:
            return HttpResponse(json.dumps({"error":True,"product":"-"}))
    raise PermissionDenied()

####################################################


@login_required
def send_first_email(request,device_id,challenge):
    if "activation_%s"%device_id in request.session:
        return HttpResponseRedirect(reverse(devices_list)+"?failed")    
    
    get_object_or_404(DeviceChallengeToken,device__id=device_id, token=challenge, is_used=False)
    device = Device.objects.get(id=device_id)
    url = reverse('apps.devices.views.mobileconfig_static', args=(challenge,))
    mobileconfig_url = "https://www.PROJECT.ir{}".format(url)
    analytics.track(device.user.id.user_id, 'create_account', {
        "mobileconf_url": mobileconfig_url,
        "email": device.user.username
    })
    
    request.session["activation_%s"%device_id] = True
    return HttpResponseRedirect(reverse(devices_list)+"?success")

def is_free_device(device):
    """Get a device model object and check if it has free device data
    """
    idfv = device.idfv
    aid = device.aid
    uuid = device.uuid

    if idfv and aid and uuid:
        return True
    else:
        return False

@login_required
def devices_list(request):
    class DeviceInfo:
        def calculate_remaining_days_to_activate_device(self,jdate,dev_status):
            if dev_status != 7: return None
            return (jdate-timezone.now()).days+1
        def free_device(self, dev_id, campaigns, registered=False):
            self.id = dev_id
            self.registered = registered
            self.product = ""
            self.ptype = ""
            self.plan_label = "free"
            if campaigns:
                last_camp = max(campaigns.items(), key=operator.itemgetter(1))
                j = last_camp[1]
                self.campaigns = jdatetime.date.fromgregorian(day=j.day,month=j.month,year=j.year).strftime("%Y/%m/%d")
            else:
                self.campaigns = "بدون انقضا"
            self.link = settings.AFABASIC_DL_LINK
            return self

        def registered_device(self,Id, product, plan_label, invoice_date, invoice_url,dev_id,paid,next_label,dev_status,datetime_object):
            self.id = Id
            self.registered = True
            self.product = get_idevice_from_internal_name(product)
            self.ptype = "iphone" if "iphone" in product.lower() else "ipad"
            self.plan_label = plan_label
            self.invoice_date = invoice_date
            self.invoice_url = invoice_url
            self.activation_link = None
            self.invoice_issued = False
            self.paid_not_active_days = self.calculate_remaining_days_to_activate_device(datetime_object,dev_status)
            if not paid:
                self.invoice_issued = True
                self.future_plan_label = next_label
            
            self.link = "#"
            try:
                device = Device.objects.filter(device_id=dev_id).reverse()[0]
                self.link = reverse('unique_download_ipa', kwargs={'uuid': str(device.uniq_name)})
            except: pass
            return self
        def unregistered_device(self,dev_id,plan_label,invoice_date,invoice_url,paid,next_label,dev_status,datetime_object):
            self.id = dev_id
            self.registered = False
            self.product = ""
            self.ptype = ""
            self.plan_label = plan_label
            self.invoice_date = invoice_date
            self.invoice_url = invoice_url
            self.paid_not_active_days = self.calculate_remaining_days_to_activate_device(datetime_object,dev_status)
            try:
                token = DeviceChallengeToken.objects.filter(device__id=dev_id,is_used=False).order_by('-id')[0].token
                url = reverse(send_first_email, kwargs={'device_id': dev_id,'challenge' : token})
                self.activation_link = url
            except Exception as e:
                print e
                self.activation_link = None
            self.invoice_issued = False
            if not paid:
                self.invoice_issued = True
                self.future_plan_label = next_label
            
            self.link = "#"
            return self

    def f(dev):
        tup = f5.device_details(request, dev.id)
        
        if tup == ('','') or not tup:
            user_info = appdb.users.find_one({'user_id': str(dev.user.id.user_id),
                                              "device": str(dev.pk)})
            if is_free_device(dev) and user_info:
                campaigns = user_info.get('campaigns', None)
                return DeviceInfo().free_device(dev.id, campaigns)
            else:
                return None
        try:
            j = dateutil.parser.parse(tup[2][u'due_date'])
            date = jdatetime.date.fromgregorian(day=j.day,month=j.month,year=j.year).strftime("%Y/%m/%d")
            print tup[0]
            if dev.device_id is None:
                return DeviceInfo().unregistered_device(dev.id,tup[1][u'label'], date,
                    reverse(invoice_of_device, kwargs={'device_id': dev.id}),tup[0][u'paid'],tup[0][u'plan_label'],tup[2]['status'],j)
            else:
                return DeviceInfo().registered_device(dev.id,dev.device_product,
                    tup[1][u'label'], date,
                    reverse(invoice_of_device, kwargs={'device_id': dev.id}),dev.device_id,
                    tup[0][u'paid'],tup[0][u'plan_label'],tup[2]['status'],j
                )
        except:
            import traceback
            traceback.print_exc()
            return None
    
    devices_list=filter(None,map(f, Device.objects.filter(user=request.user)))
    display_notadd = 'none'
    display_slide_success = 'block' if 'success' in request.GET else 'none'
    display_slide_error = 'block' if 'failed' in request.GET else 'none'
    activation_link_notadd = None
    paid_not_active_days = None
    if len(devices_list) == 1 \
       and not devices_list[0].plan_label == "free" \
       and not devices_list[0].registered:
        display_notadd = 'block'
        activation_link_notadd = devices_list[0].activation_link
        paid_not_active_days = devices_list[0].paid_not_active_days
        devices_list = []

    variables = dict(
        user_avatar=get_avatar_url(request.user),
        user=request.user,
        devices_list=devices_list,
        display_notadd=display_notadd,
        display_slide_success=display_slide_success,
        display_slide_error=display_slide_error,
        activation_link_notadd=activation_link_notadd,
        paid_not_active_days=paid_not_active_days,
    )
    
    return render_to_response(
        'mydevices.html',
        RequestContext(request, variables)
    )

from apps.appbuy.models import BoughtApp

@login_required
def bought_apps(request):
    bought_apps_list=filter(None, BoughtApp.objects.filter(user=request.user))

    variables = dict(
        user_avatar=get_avatar_url(request.user),
        bought_apps_list=bought_apps_list,
        user=request.user
    )

    return render_to_response(
        'myboughtapps.html',
        RequestContext(request, variables)
    )

from django.shortcuts import get_object_or_404

@login_required
def invoices_list(request,device_id=None,show_payments=True):
    class InvoiceInfo:
        def __init__(self, invoice_stat,plan_label, plan_amt, invoice_amt, invoice_url,payment_url,device_type):
            if device_type:
                self.device_type = "iphone" if "iphone" in device_type.lower() else "ipad"
            else:
                self.device_type = "-"
            self.invoice_stat = invoice_stat
            self.plan_label = plan_label
            self.plan_amt = plan_amt
            self.invoice_amt = invoice_amt
            self.discount_amt = self.plan_amt - self.invoice_amt
            self.invoice_url = invoice_url
            self.payment_url = payment_url or None
    class PaymentInfo:
        def __init__(self, res):
            j = dateutil.parser.parse(res['pay_time'])
            self.date = jdatetime.date.fromgregorian(day=j.day,month=j.month,year=j.year).strftime("%Y/%m/%d")
            self.price = res['amount']
            self.device = "-"
            if res["device_id"]:
                self.device = Device.objects.get(id=int(res["device_id"]))
                if self.device and self.device.device_product:
                    self.device = self.device.device_product
                else:
                    self.device = "-"
                    
            self.device = get_idevice_from_internal_name(self.device)
            
            self.link = None
            if res["invoice"]:
                self.link = request.build_absolute_uri(reverse(invoice_details,args=(res["invoice"],)))
    def f(dev):
        if device_id and str(dev.id) != str(device_id):
            return None
        tup = f5.device_details(request, dev.id)
        if tup == ('','') or not tup:
            return None
        if str(tup[2]['status']) in ['2','7']:
            return None
        return InvoiceInfo('paid',
            tup[0][u'plan_label'], tup[0][u'plan_amount'], tup[0][u'amount'],
            reverse(invoice_details, kwargs={'invoice_id': tup[0]['id']}),tup[0][u'invoice_payment_url'][u'mellat'],dev.device_product
        )
    
    if device_id:
        get_object_or_404(Device,pk=int(device_id),user=request.user)
    f5_pay = f5.payment_details(request,request.user.id.user_id)
    variables = dict(
        user_avatar=get_avatar_url(request.user),
        user=request.user,
        invoices_list=filter(None,map(f, Device.objects.filter(user=request.user))),
        payments = map(PaymentInfo,f5_pay),
        show_payments = show_payments,
    )
    
    return render_to_response(
        'myinvoices.html',
        RequestContext(request, variables)
    )

def get_avatar_url(user):
    """Get a user name and return its avatar URL
    """
    user_obj = Device.objects.filter(user=user)[0].user.avatar
    return user_obj.url if user_obj else None

@login_required
def profile(request):
    upd_success = upd_error = error_msg = False
    user = request.user
    user_avatar = get_avatar_url(user)
    if request.method == 'POST':
        avatar_form = AvatarUpload(request.POST, request.FILES)
        name = request.POST['name']
        email = request.POST['email']
        passw = request.POST['pass']
        mobile = request.POST['mobile_number']
        alter = False

        if email != "" and email != user.email:
            email = email.lower()
            user.username = user.email = email
            user.id.email = email
            user.id.save()
            alter = True
        user.first_name = name
        if mobile != "":
            if re.match(r'09[0-9]{9}', mobile):
                user.mobile_number = mobile
            else:
                error_msg = "شماره موبایل وارد شده نامعتبر است."
        if passw != "":
            # Clean all anonymous api token recores
            redis_client.delete(user.id.user_id)
            # Set password
            user.set_password(passw)
        try:
            validate_email(email)
            if not re.match(r'^.{8,64}$', passw):
                raise ValidationError("رمز عبور حداقل باید ۸ کاراکتر داشته باشد")
            user.full_clean()
            user.save()
            for device in Device.objects.filter(user=user):
                device.email = user.email
                device.save()
            analytics.identify(user.id.user_id, {
                "firstName" : user.first_name,
                "email": user.email
            })
            if alter:
                alter_url = settings.FPAN['host'] + settings.FPAN['urls']['alter_user']
                r = requests.post(alter_url,verify=False, headers=f5.get_api_header(),data = {
                        "user_id": user.id.user_id,
                        "email" : email
                    })
                analytics.track(user.id.user_id,"user_changed_profile",{
                    "firstName" : name,
                    "email": email
                })
                js = r.json()
                js["success"]
            
            if avatar_form.is_valid():
                user_obj = Device.objects.filter(user=user)[0].user
                avatar_img = avatar_form.clean_avatar()
                if avatar_img:
                    user_obj.avatar = avatar_form.clean_avatar()
                    user_obj.save()
                    # Returning page like this will make user to see avatar
                    # changing result just after uploading it. No refresh is
                    # necessairy.
                    return HttpResponseRedirect('/panel/profile/')
                else:
                    raise ValidationError("عکس آپلود شده باید دارای یکی از فرمت‌ها JPEG, PNG و یا GIF بوده و دارای حجمی کمتر از ۳۰۰ کیلوبایت باشد.")

            upd_success=True
        except ValidationError as e:
            import sys
            print sys.exc_info()
            error_msg = e.message

    variables = dict(
        error_msg=error_msg,
        user_avatar=user_avatar,
        user=request.user,
        upd_success=upd_success,
        upd_error=upd_error
    )
    context = RequestContext(request, variables)
    context.update(csrf(request))
    return render_to_response(
        'myprofile.html',
        context
    )



def parse_plans(request):
    #Amir: Coded From plans.js in Vitrine
    json_resp = requests.get(request.build_absolute_uri(reverse('plans_list')),verify=False).json()
    json_resp = [x for x in json_resp if x['is_active']]
    json_resp.sort(key=lambda k:int(k["price"]))
    i = 1
    PROJECT_daily_rate = None
    for plan in json_resp:
        if not PROJECT_daily_rate:
            PROJECT_daily_rate = plan["price"]/plan["period_length"]
        plan["period_length"] = int(plan["period_length"])
        plan["orig_price"] = int(plan["period_length"]*PROJECT_daily_rate)
        plan["discount"] = int(plan["orig_price"]-plan["price"])
        plan["free"] = plan["discount"]/PROJECT_daily_rate
        plan["free"] = plan["free"] if plan["free"] > 0 else None
        plan["iter"] = i
        i+=1
        plan["period_length"] /= 30
        plan["price_unformatted"] = plan["price"]
        plan["price"] /= 1000
        if json_resp.index(plan) == 1:
            plan["recommended"] = True
    return json_resp
        


@login_required
def add_device(request):
    f5_settings = f5.get_settings(request)
    payment_availablity = 'block' if 'OMGPAY_DISABLE_FOR_USERS' in f5_settings and f5_settings['OMGPAY_DISABLE_FOR_USERS'] == True else 'none'
    variables = dict(
        plans = parse_plans(request),
        payment_availablity=payment_availablity,
    )
    return render_to_response('payment.html',RequestContext(request,variables))


@login_required
def change_plan(request,device_id):
    get_object_or_404(Device,id=device_id,user=request.user)
    
    tup = f5.device_details(request,device_id)
    if not tup or tup == ('',''):
        raise Http404
    
    if tup[0][u'paid']:
        raise Http404
    
    ERROR = False
    if request.method == "POST" and "active-plan" in request.POST:
        try:
            plan = request.POST["active-plan"]
            url = settings.FPAN['host'] + settings.FPAN['urls']['change_plan']
            payload = {
                'plan' : plan,
                'device_id' : device_id
            }
            r = requests.post(url, data=payload, headers=f5.get_api_header(), verify=False)
            print r.content
            if r.status_code == 200:
                from apps.devices.views import start_invoice_pay
                return HttpResponseRedirect(reverse(start_invoice_pay,kwargs={'invoice_id':r.json()['invoice_id']}))
            else:
                ERROR=True
        except:
            ERROR = True
    
    plans = parse_plans(request)
    variables = dict(
        plans = plans,
        ERROR = ERROR
    )
    return render_to_response('change_plan.html',RequestContext(request,variables))


@login_required
def welcome_device(request,invoice_id):
    request.session.cycle_key()
    class InvoiceInfo:
        def __init__(self, tup,plan,srid):
            self.plan_label = tup[u'plan_label']
            self.plan_amt = tup[u'plan_amount']
            self.invoice_amt = tup[u'amount']
            self.discount_amt = self.plan_amt - self.invoice_amt
            self.invoice_url = tup[u'invoice_payment_url'][u'mellat']
            self.sale_refrence_id = srid

    def f():
        tup = f5.invoice_details(request, invoice_id)
        if tup == {} or not tup:
            return None
        plan = f5.plan_details(request, tup[u'plan'])
        get_object_or_404(Device,pk=int(tup[u'subscription'][u'uuid']),user=request.user)
        return InvoiceInfo(tup,plan,f5.sales_refrence_id(request,invoice_id))
    
    variables = dict(
        user=request.user,
        invoice = f(),
        is_invoice = "invoice_id" in request.session
    )
    return render_to_response('payment-back.html',RequestContext(request,variables))


def gift_thanks(request):
    if not 'getter_name' in request.session:
        raise Http404
    session = deepcopy(request.session)
    request.session.clear()
    return render_to_response('gift-payment.html',session)


@login_required
def invoice_of_device(request,device_id):
    return invoices_list(request,device_id=device_id,show_payments=False)


@login_required
def invoice_details(request,invoice_id):
    class InvoiceInfo:
        def __init__(self, tup,plan,srid,dev_id):
            self.device_id = dev_id
            self.invoice_stat = 'paid' if tup[u'paid'] else 'unpaid'
            j = dateutil.parser.parse(tup[u'created_at'])
            self.created_at = jdatetime.date.fromgregorian(day=j.day,month=j.month,year=j.year).strftime("%Y/%m/%d")
            self.plan_label = tup[u'plan_label']
            self.plan_amt = tup[u'plan_amount']
            self.invoice_amt = tup[u'amount']
            self.discount_amt = self.plan_amt - self.invoice_amt
            self.sale_refrence_id = srid
            if self.invoice_stat== 'paid':
                j = dateutil.parser.parse(tup[u'pay_time'])
                self.pay_date = jdatetime.date.fromgregorian(day=j.day,month=j.month,year=j.year).strftime("%Y/%m/%d")
            else:
                #change mellat to index later
                self.invoice_url = tup[u'invoice_payment_url'][u'mellat']

    def f():
        tup = f5.invoice_details(request, invoice_id)
        if tup == {} or not tup:
            return None
        plan = f5.plan_details(request, tup[u'plan'])
        dev = get_object_or_404(Device,pk=int(tup['subscription']['uuid']),user=request.user)
        return InvoiceInfo(tup,plan,f5.sales_refrence_id(request,invoice_id),dev.id)
    
    variables = dict(
        user=request.user,
        invoice = f()
    )
    return render_to_response(
        'invoice.html',
        RequestContext(request, variables)
    )


def error_code_parse(rescode):
    codes = {
        "421" : "IP نامعتبر است",
        "55" : "تراکنش نامعتبر است",
        "61" : "‫خطا در واریز",
        #PLEASE Complete THIS
        
    }
    if rescode in codes:
        return codes[rescode]
    else:
        return "پرداخت ناموفق"


@login_required
def invoice_fail(request,ResCode):
    class InvoiceInfo:
        def setDataforDevice(self, plan):
            self.plan_label = plan[u'label']
            self.plan_amt = int(plan[u'price'])
            self.invoice_amt = int(request.session["price"])
            self.discount_amt = self.plan_amt - self.invoice_amt
            self.invoice_url = request.build_absolute_uri("/panel/pay/mellat")
            return self
        def setDataforInvoice(self,price,plan,inv_id):
            self.plan_label = plan[u'label']
            self.plan_amt = int(plan[u'price'])
            self.invoice_amt = int(price)
            self.discount_amt = self.plan_amt - self.invoice_amt
            self.invoice_url = request.build_absolute_uri("/panel/pay/mellat/%s" % inv_id)
            return self

    def f():
        if "invoice_id" in request.session:
            invoice = f5.invoice_details(request, request.session["invoice_id"])
            plan = f5.plan_details(request, invoice['plan'])    
            return InvoiceInfo().setDataforInvoice(invoice['amount'],plan,request.session['invoice_id'])
        plan = f5.plan_details(request, request.session["plan"])
        return InvoiceInfo().setDataforDevice(plan)
    
    variables = dict(
        user=request.user,
        invoice = f(),
        error_result = error_code_parse(ResCode)
    )
    return render_to_response('payment-failure.html',RequestContext(request,variables))


@login_required
def referral(request):
    username = request.user
    user_obj = User.objects.get(username=username)
    user_id = user_obj.id.user_id
    variables = dict(
        user_id=user_id,
    )
    return render_to_response('referral.html', RequestContext(request,
                                                              variables))

@login_required
def dashboard(request):
    levels = {1: "25",
              2: "50",
              3: "75",}
    username = request.user
    user_obj = User.objects.get(username=username)
    # referred_num = UserReferral.objects.filter(referrer_user=user_obj).count()
    user_points, c = UserPoints.objects.get_or_create(user=user_obj)
    period_points = user_points.period_points
    fixed_points = period_points if period_points <= len(levels) else len(levels)
    next_level = len(levels) - fixed_points
    variables = dict(
        this_month_referreds=period_points,
        next_level= next_level,
        current_discount = levels.get(fixed_points, 0),
        progress_length = 100 - (next_level * (100/len(levels))),
        levels=levels,
    )
    return render_to_response('mydashboard.html', RequestContext(request,
                                                                 variables))
