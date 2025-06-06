import logging

logger = logging.getLogger(__name__)

class LogLongURIMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        uri = request.get_full_path()
        if len(uri) > 500:
            logger.warning(f"Long URI detected: method={request.method}, uri={uri[:100]}..., length={len(uri)}")
        response = self.get_response(request)
        return response