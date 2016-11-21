from django.http import HttpResponseForbidden
from django.contrib.auth import authenticate, login
from django.views.decorators.csrf import csrf_exempt

from apps.users.models import UserEmail, User

from functools import wraps
from views import RedisClient

def decode_value(value):
    return value.decode('base64').decode('hex')


def token_required(view_func):
    """Decorator which ensures the user has provided a correct user and token pair."""

    @csrf_exempt
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = None
        token = None
        basic_auth = request.META.get('HTTP_AUTHORIZATION')

        user = request.POST.get('user', request.GET.get('user'))
        token = request.POST.get('token', request.GET.get('token'))

        if not (user and token) and basic_auth:
            auth_method, auth_string = basic_auth.split(' ', 1)

            if auth_method.lower() == 'basic':
                auth_string = auth_string.strip().decode('base64')
                user, token = auth_string.split(':', 1)
                user = authenticate(pk=user, token=token)

            # This method will get a valid user_id and authentication token to
            # authenticate user and login
            elif auth_method.lower() == 'secret':
                auth_string = auth_string.strip()
                user_id, token = auth_string.split(':', 1)

                if RedisClient.get(token):
                    try:
                        email_obj = UserEmail.objects.get(user_id=user_id)
                        user = User.objects.get(id=email_obj)
                    except:
                        return HttpResponseForbidden("Invalid user_id.")

                    return view_func(request, *args, **kwargs)
                else:
                    return HttpResponseForbidden('Token expired!')

        if not (user and token):
            return HttpResponseForbidden("Must include 'user' and 'token' parameters with request.")

        if user:
            login(request, user)
            return view_func(request, *args, **kwargs)

        return HttpResponseForbidden()
    return _wrapped_view
