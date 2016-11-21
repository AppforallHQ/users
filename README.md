Dependencies
------------

These would be installed with puppet

- [python (2.7)](https://wiki.debian.org/Python#Python_in_Debian) and python-dev
- [postgresql](https://wiki.debian.org/PostgreSql)
- [foreman](https://github.com/ddollar/foreman)
- [git-deploy](https://github.com/mislav/git-deploy) on local machine

To get more information about installing this packages you can use links
provided above.

Development
===========

After installing dependencies you have to run a `Postgresql` instance and after
that try to run users.  A typical tmuxinator window would be like:

    - fpan:
        pre:
          - cd users
          - source .virtualenv/bin/activate
        layout: main-horizontal
        panes:
          - foreman run deploy/setup
          - foreman run python manage.py runserver 0.0.0.0:8006
          - foreman run python manage.py celery worker

Now `users` application will served on localhost:8006.

Deployment
==========

By now you should've installed
*   `orch` and
*   `vitrine`
on the production server.

Deploy
------

*   Add a remote to your local git clone

        git remote add host user@host.FQDN:/app/users

*   Initiate remote git remote and deploy hooks on the remote server

        git deploy setup -r host

*   Push to remote (same tips about `production` branch apply here)

        git checkout production
        git merge master

    and then

        git push host production:master
        git checkout master

API
===

## AppBuy


### Installation
After installing and running `users` if you want to run it in your `localhost` you have to have a running instance of `AFAPI` project (or you can change it to production servers address).

There is also a need of a running instance of `Redis` which have to contain a key named `dollar_change` (int) which will be used to calculate applications price in Rials.

### Usage
Right now `users` provides two major API to handle `AppBuy` process using `F5` Backend. These two API will provide order initialization process and manipulations steps.

### Token authentication.

To use some of our public APIs you need to be authenticated by our token
authontication system.

To get a valid token you have to send a POST request to:

    http://127.0.0.1:8005/token/new.json

Containing POST data: username & password. The result will be a JSON containing
your user_id and a valid token (expires every 7 days).

After that you can put an `Authorization` header containing `b64encode`ed value of data you get formated like this:

    TOKEN['user'] + ':' + TOKEN['token']

As an example of usage you can see `apps.panel.f5adapter.get_api_header`.

TODO: Use a better API address for this and make a reusable and independent module.

#### Available APIs
##### Order initialization (No Authentication) (AppBuy):
To initialize an `AppBuy` order you have to use:

    /panel/appbuy/init/
    
Which needs three `GET` request type arguments:

1. `userid`: Which is the `UserEmail` object model id.
2. `appid`: Or application `itunes id`.
3. `PROJECT2`: Which has to be a valid email address.

Giving all this arguments user will be able going through payment process and finish it in url `/panel/appbuy/thanks/` which contains all orders data as arguments and an special `JavaScript` function which will return order status as a `JSON` object:
    
    function userPaymentStatus() {
	    return "OK, {{order_id}}";
    }

##### Change order status (AppBuy)
The second API is the one which will give you the ability to manipulate an order status field:

    /panel/appbuy/api/change_status/
    
This one will take two `POST` request type arguments as follow:

1. `order_id`: Which makes it able to find appropriate order object. You can find it using `userPaymentStatus` function from last code sample.
2. `status` Which is a number between 4 to 7 and will give the order object model the following minings:
    + 4 => Evaluating the order process is started.
    + 5 => Process failed.
    + 6 => Process succeeded.

##### Get users bought apps (AppBuy)
This API will help you to get a list of apps user bought using `AppBuy` subsystem.

    /panel/appbuy/api/app_list/

Which assume you will pass a POST argument (named `user_id`) to it. It will
return a JSON list of bought apps containing their `appname`, `itunes_id`,
`appstore_url` and `icon` details. If user didn't buy any apps you will get an
empty list.

If you call it using a wrong `user_id` you will get a 404. If you call it
withoud user_id you will get `{error: True}`.

##### Check if user bought an app before (AppBuy)
Another API which user's `AppBuy` provides is:

    /panel/appbuy/api/app_check/

This one is a little tricky. It assumes you will pass it a `user_id` and an apps `app_id` (aka: itunes id) and in response:

- If user bought that app before you will get an JSON response containing `status: False` and a list of used `apple_id`'s to buy this app as `ids`.
- If user doesn't bought the app you will get an JSON response containing `status: True`.
- In any case you pass it wrong `user_id` or no `user_id/app_id` you will get either 404 or `error: True` (same as previous API)

Be aware that this API will not check existence of an itunes id.

#### Return users last used apple id (AppBuy)
You can get user's last used `apple_id` by calling:

    /panel/appbuy/api/last_PROJECT2/

Which takes a `user_id` in POST request and returns user's last used `apple_id` if exists or user's email address if not. In case of passing a wrong user_id you will get an 404 error.

#### Error Reporting (AppBuy)
Every exception occured in this process will cause user to end up in URL `/panel/appbuy/error/` Which will give user an appropriate message about the cause of exception and a `JavaScript` function like this to make you able catch the status:

    function userPaymentStatus() {
	   return "{{err_code}}, {{err_msg}}"
    }

##### Error codes (AppBuy)
1. Something wrong with the GET request data to `/panel/appbuy/init/`
2. AFAPI is not responding or the resulting `JSON` objects contains no values.
3. Redis is down or `dollar_change` key is not set.
4. F5's `Generic API` throw an error in initialization phase.
5. The order id reported to page `/panel/appbuy/thanks/` is not valid or there is no order id in variables (This will happen) when user tries to refresh thanks page which all session variables are flushed.
6. Payment failed (By user/bank)
7. Users callback session authentication failed

PS: `users`'s `AppBuy` API is based on `F5`'s `Generic` Api. There may some problem happens on that side of process which `F5` will handle them by itself. 

#### Get user status API
In the mean time there are two endpoints to get user status:

1. /panel/get_status/               (paid users)
2. /panel/basic_user_status/        (basic users)

Return value of this calls contains status related data + a `user_status` field which is different by request type and user:

1. user is active and can have download requests
2. user is unpaid and can't have download requests
3. user is blocked
4. user is registered by related email address is not activated. (basic_user_status endpoint, can't have download requests)
