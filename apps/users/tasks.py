from django.template.loader import get_template
from django.template import Context
from celery import task

import analytics
import os

@task
def send_email_via_segmentio(to, params, email_type, templateData=None):

    if templateData:
        template = get_template(templateData['name'])
        context = Context(templateData['variables'])
        htmlContent = template.render(context).encode('utf8')
    if not params:
        params = {}
    params['content'] = htmlContent

    properties = {
        'params': params,
    }
    analytics.identify(user_id=to, traits={
        'email': to,
    })
    analytics.track(user_id=to, event=email_type, properties=properties)
