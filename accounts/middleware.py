from django.http import HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin


class BlockedUserMiddleware(MiddlewareMixin):
    def process_request(self, request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated and getattr(user, "is_blocked", False):
            return HttpResponseForbidden("Cont blocat.")
        return None
