from django.shortcuts import redirect, render

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_http_methods

@login_required
def home(request):
    return render(request, 'home.html')


def index(request):
    return render(request, 'index.html')


@login_required
def scrap(request):
    if not request.user.puede_gestionar_scrap:
        return redirect('home')

    return render(request, 'scrap.html')


def login_view(request):
    return render(request, 'login.html')




@login_required
@require_GET
def api_notificaciones(request):
    return JsonResponse({
        'notificaciones': []
    })


@login_required
@require_http_methods(["DELETE"])
def eliminar_notificacion(request, notificacion_id):
    return JsonResponse({
        'ok': True
    })
    
