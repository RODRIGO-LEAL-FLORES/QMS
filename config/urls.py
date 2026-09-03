from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from core import views as core_views

urlpatterns = [
    path('', core_views.index, name='index'),

    path('admin/', admin.site.urls),
    
    
     # USUARIOS
    path(
        'usuarios/',
        include('apps.usuarios.urls')
    ),

    path(
        'reclamaciones/',
        include('apps.reclamaciones.urls')
    ),

    path(
        'reclamaciones-internas/',
        include('apps.reclamaciones_internas.urls')
    ),

    path(
        '',
        include('core.urls')
    ),
    
    path(
        'liberaciones/',
        include('apps.liberaciones.urls')
    )
]

urlpatterns += static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT
)
    
