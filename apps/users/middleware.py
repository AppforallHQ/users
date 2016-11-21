class DisableCSRF(object):
    def process_request(self, request):
        # because i use Ajax call and form submit from another system i need it
        setattr(request, '_dont_enforce_csrf_checks', True)
