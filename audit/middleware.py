import threading

_local = threading.local()


def get_current_user():
    """Reads `request.user` lazily, at call time — not a snapshot taken when
    the middleware first runs. DRF's JWT authentication resolves `request.user`
    *inside* view dispatch (after Django's middleware chain has already
    started), and syncs the result back onto this same request object, so a
    value captured too early would always be AnonymousUser."""
    request = getattr(_local, "request", None)
    if request is None:
        return None
    return getattr(request, "user", None)


class CurrentUserMiddleware:
    """Stashes the request object in a thread-local so model signals — which
    have no access to the request — can still attribute changes to whoever
    made them."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _local.request = request
        try:
            return self.get_response(request)
        finally:
            _local.request = None
