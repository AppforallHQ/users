import os

from django.conf import settings
from django.db.utils import IntegrityError
from django.contrib.sites.models import Site
from django.db import DEFAULT_DB_ALIAS as database

import django
django.setup()

from apps.users.models import User,UserEmail

if User.objects.filter(username="admin").exists():
    print "Admin user already exists"
else:
    uid = UserEmail(email='joe@rubako.us',user_id=1)
    uid.save()
    User.objects.db_manager(database).create_superuser('admin', 'joe@rubako.us', 'password',id=uid)

print "Updating default site"

current_site = Site.objects.get_current()
old_domain = current_site.domain
current_site.domain = settings._DOMAIN
current_site.save()

print "... domain changed from %s to %s" % (old_domain, current_site.domain)
