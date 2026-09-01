from django.core.cache import cache
from django.db import connection
from django.http import HttpResponse, JsonResponse


class HealthCheckMiddleware:
    """
    Answers Kubernetes probes before any other middleware runs — in
    particular before ALLOWED_HOSTS is enforced, since kubelet sends the
    pod IP as the Host header. Placing it first also keeps probe traffic
    out of the Prometheus metrics.

    /healthz/ — liveness: the process is up and can serve a request.
    /readyz/  — readiness: dependencies (DB, cache) are reachable;
                returns 503 while any of them is down so the pod is
                pulled out of the Service until it recovers.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path in ('/healthz', '/healthz/'):
            return HttpResponse('ok', content_type='text/plain')
        if request.path in ('/readyz', '/readyz/'):
            return self._readyz()
        return self.get_response(request)

    def _readyz(self):
        checks = {}

        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
            checks['database'] = 'ok'
        except Exception as exc:
            checks['database'] = f'error: {exc}'

        try:
            cache.set('readyz', '1', 5)
            checks['cache'] = 'ok' if cache.get('readyz') == '1' else 'error: readback failed'
        except Exception as exc:
            checks['cache'] = f'error: {exc}'

        healthy = all(value == 'ok' for value in checks.values())
        return JsonResponse(checks, status=200 if healthy else 503)
