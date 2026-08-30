from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    """Wraps DRF's default error body in the {code, message, detail} shape used
    across the API (see §17 of the technical documentation)."""
    response = exception_handler(exc, context)
    if response is None:
        return None

    code = getattr(exc, "default_code", exc.__class__.__name__.lower())
    response.data = {
        "code": code,
        "message": str(exc),
        "detail": response.data,
    }
    return response
