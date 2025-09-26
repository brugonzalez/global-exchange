from django.conf import settings
from django.shortcuts import redirect

def SesionExpiradaMiddleware(get_response):
    """
    Redirige al login con ?exp=1 cuando:
      - El navegador aún envía la cookie 'sessionid'
      - request.user ya NO está autenticado (sesión expirada)
      - La URL no es el login ni un recurso estático
    """
    def middleware(request):
        tenia_cookie = 'sessionid' in request.COOKIES
        autenticado = request.user.is_authenticated

        if (
            tenia_cookie
            and not autenticado
            and request.path != settings.LOGIN_URL
            and not request.path.startswith('/static/')
        ):
            return redirect(f"{settings.LOGIN_URL}?exp=1&next={request.path}")
        return get_response(request)
    return middleware