from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        code = getattr(exc, "default_code", "error")
        message = str(exc.detail) if hasattr(exc, "detail") else str(exc)
        detail = {}

        if isinstance(exc.detail, dict):
            detail = exc.detail
            message = exc.__class__.__name__
        elif isinstance(exc.detail, list):
            detail = {"messages": exc.detail}
            message = exc.__class__.__name__

        response.data = {
            "error": {
                "code": code,
                "message": message,
                "detail": detail,
            }
        }

    return response
