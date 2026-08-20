from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        code = getattr(exc, "default_code", "error")
        exception_detail = getattr(exc, "detail", None)
        message = str(exception_detail) if exception_detail is not None else str(exc)
        detail = {}

        if isinstance(exception_detail, dict):
            detail = exception_detail
            message = exc.__class__.__name__
        elif isinstance(exception_detail, list):
            detail = {"messages": exception_detail}
            message = exc.__class__.__name__

        response.data = {
            "error": {
                "code": code,
                "message": message,
                "detail": detail,
            }
        }

    return response
