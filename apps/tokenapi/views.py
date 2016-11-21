import random
import string
import redis
from django.contrib.auth import authenticate
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

try:
    from django.contrib.auth import get_user_model
except ImportError: # Django < 1.5
    from django.contrib.auth.models import User
else:
    User = get_user_model()

from tokens import token_generator
from http import JsonResponse, JsonError, JsonResponseForbidden, JsonResponseUnauthorized

# Setup Redis client
RedisClient = redis.StrictRedis(host=settings.REDIS_HOST,
                                port=settings.REDIS_PORT, db=settings.TOKEN_BACKEND)


def string_token(length):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))


def gen_token(username, password, device=None, safe=False):
    user = authenticate(username=username, password=password)
    if user:
        TOKEN_CHECK_ACTIVE_USER = getattr(settings, "TOKEN_CHECK_ACTIVE_USER", False)
        if TOKEN_CHECK_ACTIVE_USER and not user.is_active:
            return JsonResponseForbidden("User account is disabled.")

        if safe:
            token = string_token(100)
            user_id = user.id.user_id

            try:
                data = {'user_id': user_id, 'device': device}

                if device and RedisClient.hmset(name=token, mapping=data):
                    RedisClient.expire(name=token, time=settings.TOKEN_TIMEOUT)
                    data['token'] = token

                else:
                    raise
            except:
                data = {'error': 'Something went wrong!'}
        else:
            data = {
                'token': token_generator.make_token(user),
                'user': user.pk,
            }

        return JsonResponse(data)
    else:
        return JsonResponseUnauthorized("Unable to log you in, please try again.")


# Creates a token if the correct username and password is given
# token/new.json
# Required: username&password
# Returns: success&token&user
@csrf_exempt
def token_new(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        if username and password:
            return gen_token(username, password)
        else:
            return JsonError("Must include 'username' and 'password' as POST parameters.")
    else:
        return JsonError("Must access via a POST request.")


# Creates a safe token with database backend if username and password is given
# token/get
# Required: username&password
# Returns: success&token&user
@csrf_exempt
def get_safe_token(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        device = request.POST.get('device')

        if username and password and device:
            return gen_token(username, password, device=device, safe=True)
        else:
            return JsonError("Must include 'device', 'username' and 'password' as POST parameters.")
    else:
        return JsonError("Must access via a POST request")

# Checks if a given token and user pair is valid
# token/:token/:user.json
# Required: user
# Returns: success
def token(request, token, user):
    try:
        user = User.objects.get(pk=user)
    except User.DoesNotExist:
        return JsonError("User does not exist.")

    TOKEN_CHECK_ACTIVE_USER = getattr(settings, "TOKEN_CHECK_ACTIVE_USER", False)

    if TOKEN_CHECK_ACTIVE_USER and not user.is_active:
        return JsonError("User account is disabled.")

    if token_generator.check_token(user, token):
        return JsonResponse({})
    else:
        return JsonError("Token did not match user.")

# Get a token and return it's related username retrived from redis
# token/get
# Required: token
# Returns: username
def token_to_username(request):
    token = request.GET.get("token", None)
    if token:
        try:
            user_data = RedisClient.hgetall(token)
            user_obj = User.objects.filter(id__user_id=user_data["user_id"])
            if user_data and user_obj:
                return JsonResponse({"user_id": user_data["user_id"],
                                     "username": user_obj[0].username,
                                     "device": user_data["device"]})
        except:
            pass
    return JsonError("Bad request")
