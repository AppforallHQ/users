"""Adapter for fpan RESTful API."""

import requests as r
import json, re
from base64 import b64encode
from django.conf import settings

def _base_url(request):
    return settings.FPAN["host"]


def _url_subscriptions(baseurl): 
    return baseurl+settings.FPAN['urls']['subscribe']


def _url_plans(baseurl):
    return baseurl+settings.FPAN['urls']['plans']


def _url_invoices(baseurl): 
    return baseurl+settings.FPAN['urls']['invoice']

def _url_payment(baseurl): 
    return baseurl+settings.FPAN['urls']['bankpayment']

def _url_settings(baseurl):
    return baseurl+settings.FPAN['urls']['settings']

_F5_UID = settings.FPAN['auth']['username']
_F5_PWD = settings.FPAN['auth']['password']

# Global variable for TOKEN helps to have generated token as long as
# supportpanel is running [top 7 days since users api will expire it.]
TOKEN = None

def get_api_token():
    """ Get a token from users API and set it to TOKEN global variable.
    """
    global TOKEN
    try:
        TOKEN = r.post('http://FPAN_PATH/token/new.json', data={'username': _F5_UID, 'password': _F5_PWD}).json()
    except:
        pass


def check_api_token():
    """ Check if provided token is valid or not. If not get a new token.
    """
    try:
        res = r.get('http://FPAN_PATH/token/' + TOKEN['token'] + '/' + str(TOKEN['user']) + '.json').json()
        
        if res['success'] == True:
            return
        else:
            raise
    except:
        get_api_token()


def get_api_header():
    """Generate an authorization header to use in our API calls
    """
    if not TOKEN:
        get_api_token()
    else:
        print("Check API")
        check_api_token()
    token_str = str(TOKEN['user']) + ":" + TOKEN['token']
    auth_value = 'Basic '.encode('ascii') + b64encode(token_str.encode('ascii'))
    return {'Authorization': auth_value}

def device_details(request, uuid,activate=False):
    """Return the details of a device as a tuple (plan, invoice).

    Params:
    +request+: HTTP request
    +uuid+: Device ID (aka udid)
    """
    header = get_api_header()
    resp = r.get(_url_subscriptions(_base_url(request)),
            headers=header, params={'uuid': uuid,'activate':activate},verify=False)

    #print resp.content
    if resp.status_code != 200:
        return ('', '')  # NOT SURE IF THIS IS CORRECT
    else:
        result = json.loads(resp.content)
        if result['count'] == 0:
            return ('', '')  # NOT SURE AGAIN...CHECK
        else:
            record = result['results'][0]
            invoice = invoice_details(request, record['active_invoice_id'])
            plan = plan_details(request, record['plan'])
            #print record
            return (invoice, plan, record)

def get_subscription_data(request, uuid):
    """Get a uuid and return it's related subscription serialized data from F5.
    """
    header = get_api_header()
    resp = r.get(_url_subscriptions(_base_url(request)),
                 headers=header, params={'uuid': uuid},verify=False)
    return resp.text
    

def plan_details(request, plan_id):
    """Return the details of a plan or {} in case of failure.

    Params:
    +request+: HTTP request object
    +plan_id+: Plan ID to get details
    """
    header = get_api_header()
    resp = r.get(_url_plans(_base_url(request)),
            headers=header, params={'id': plan_id},verify=False)
    if resp.status_code != 200:
        return {}
    else:
        result = json.loads(resp.content)
        if result[u'count'] == 0:
            return {}
        else:
            return result[u'results'][0]


def invoice_details(request, invoice_id):
    """Return the details of an invoice or {} in case of failure.

    Params:
    +request+: HTTP request object
    +invoice_id+: Invoice ID to get details
    """
    header = get_api_header()
    resp = r.get(_url_invoices(_base_url(request)),
            headers=header, params={'id': invoice_id},verify=False)
    if resp.status_code != 200:
        return {}
    else:
        result = json.loads(resp.content)
        if result[u'count'] == 0:
            return {}
        else:
            return result[u'results'][0]
        
        
def payment_details(request, user_id):
    header = get_api_header()
    resp = r.get(_url_payment(_base_url(request)),
            headers=header, params={'user_id': user_id},verify=False)
    if resp.status_code != 200:
        return {}
    else:
        print(resp.text)
        result = json.loads(resp.content)
        if result[u'count'] == 0:
            return {}
        else:
            return result[u'results']
        
        
def sales_refrence_id(request,invoice_id):
    header = get_api_header()
    resp = r.get(_url_payment(_base_url(request)),
            headers=header, params={'invoice_object_id': invoice_id},verify=False)

    if resp.status_code != 200:
        return '-'
    else:
        result = json.loads(resp.content)
        if result[u'count'] == 0:
            return '-'
        else:
            ret = result[u'results'][0]['sale_reference_id']
            return ret if ret != "" else "-"
    
    
def get_settings(request):
    header = get_api_header()
    resp = r.get(_url_settings(_base_url(request)),
            headers=header, verify=False)

    if resp.status_code != 200:
        return {}
    else:
        result = json.loads(resp.content)
        if result[u'count'] == 0:
            return {}
        else:
            ret = result[u'results'][0]
            return ret
