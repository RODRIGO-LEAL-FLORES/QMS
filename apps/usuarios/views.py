from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render

from .models import Usuario, Rol
from apps.areas.models import Area


def puede_administrar_usuarios(user):
    return (
        user.is_authenticated
        and user.is_active
        and user.puede_gestionar_usuarios
        and user.rol_id in (1, 2)
    )


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')

        user = Usuario.objects.filter(email=email).first()

        if user:
            usuario_autenticado = authenticate(
                request,
                username=user.username,
                password=password
            )

            if usuario_autenticado is not None:
                login(request, usuario_autenticado)
                return redirect('home')

        messages.error(request, 'Correo o contraseña incorrectos.')
        return redirect('login')

    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def usuarios(request):
    if not puede_administrar_usuarios(request.user):
        messages.error(request, 'No tienes permisos para gestionar usuarios.')
        return redirect('home')

    users = Usuario.objects.select_related('rol', 'area').all().order_by('id')
    roles = Rol.objects.all().order_by('id')
    areas = Area.objects.all().order_by('nombre')

    return render(request, 'usuarios.html', {
        'users': users,
        'roles': roles,
        'areas': areas,
    })


@login_required
def crear_usuario(request):
    if not puede_administrar_usuarios(request.user):
        messages.error(request, 'No tienes permisos para gestionar usuarios.')
        return redirect('home')

    if request.method != 'POST':
        return redirect('usuarios')

    nombre = request.POST.get('nombre', '').strip()
    email = request.POST.get('email', '').strip()
    password = request.POST.get('password', '').strip()
    rol_id = request.POST.get('rol_id')
    area_id = request.POST.get('id_area')

    if not nombre or not email or not password or not rol_id:
        messages.error(request, 'Completa los campos obligatorios.')
        return redirect('usuarios')

    if Usuario.objects.filter(email=email).exists():
        messages.error(request, 'Ese correo ya está registrado.')
        return redirect('usuarios')

    username_base = email.split('@')[0]
    username = username_base
    contador = 1

    while Usuario.objects.filter(username=username).exists():
        username = f'{username_base}{contador}'
        contador += 1

    usuario = Usuario(
        nombre=nombre,
        username=username,
        email=email,
        rol_id=rol_id,
        is_active=request.POST.get('is_active') == '1',
        puede_gestionar_reclamaciones=request.POST.get('puede_gestionar_reclamaciones') == '1',
        puede_gestionar_reclamaciones_internas=request.POST.get('puede_gestionar_reclamaciones_internas') == '1',
        puede_gestionar_reportes=request.POST.get('puede_gestionar_reportes') == '1',
        puede_gestionar_usuarios=(
            request.POST.get('puede_gestionar_usuarios') == '1'
            and rol_id in ('1', '2')
        ),
        puede_gestionar_scrap=request.POST.get('puede_gestionar_scrap') == '1',
        puede_gestionar_liberaciones=request.POST.get('puede_gestionar_liberaciones') == '1',
    )

    if area_id:
        usuario.area_id = area_id

    usuario.set_password(password)
    usuario.save()

    messages.success(request, 'Usuario creado correctamente.')
    return redirect('usuarios')


@login_required
def editar_usuario(request, id_usuario):
    if not puede_administrar_usuarios(request.user):
        messages.error(request, 'No tienes permisos para gestionar usuarios.')
        return redirect('home')

    usuario = get_object_or_404(Usuario, id=id_usuario)

    if request.method == 'GET':
        users = Usuario.objects.select_related('rol', 'area').all().order_by('id')
        roles = Rol.objects.all().order_by('id')
        areas = Area.objects.all().order_by('nombre')

        return render(request, 'usuarios.html', {
            'users': users,
            'roles': roles,
            'areas': areas,
            'edit_user': usuario,
        })

    nombre = request.POST.get('nombre', '').strip()
    email = request.POST.get('email', '').strip()
    password = request.POST.get('password', '').strip()
    rol_id = request.POST.get('rol_id')
    area_id = request.POST.get('id_area')

    if not nombre or not email or not rol_id:
        messages.error(request, 'Completa los campos obligatorios.')
        return redirect('editar_usuario', id_usuario=id_usuario)

    if Usuario.objects.filter(email=email).exclude(id=id_usuario).exists():
        messages.error(request, 'Ese correo ya pertenece a otro usuario.')
        return redirect('editar_usuario', id_usuario=id_usuario)

    usuario.nombre = nombre
    usuario.email = email
    usuario.rol_id = rol_id
    usuario.is_active = request.POST.get('is_active') == '1'
    usuario.puede_gestionar_reclamaciones = request.POST.get('puede_gestionar_reclamaciones') == '1'
    usuario.puede_gestionar_reclamaciones_internas = request.POST.get('puede_gestionar_reclamaciones_internas') == '1'
    usuario.puede_gestionar_reportes = request.POST.get('puede_gestionar_reportes') == '1'
    usuario.puede_gestionar_usuarios = (
        request.POST.get('puede_gestionar_usuarios') == '1'
        and rol_id in ('1', '2')
    )
    usuario.puede_gestionar_scrap = request.POST.get('puede_gestionar_scrap') == '1'
    usuario.puede_gestionar_liberaciones = request.POST.get('puede_gestionar_liberaciones') == '1'
    usuario.area_id = area_id if area_id else None

    if password:
        usuario.set_password(password)

    usuario.save()

    messages.success(request, 'Usuario actualizado correctamente.')
    return redirect('usuarios')


@login_required
def eliminar_usuario(request, id_usuario):
    if not puede_administrar_usuarios(request.user):
        messages.error(request, 'No tienes permisos para gestionar usuarios.')
        return redirect('home')

    if request.method != 'POST':
        return redirect('usuarios')

    usuario = get_object_or_404(Usuario, id=id_usuario)

    if usuario.id == request.user.id:
        messages.error(request, 'No puedes eliminar tu propio usuario.')
        return redirect('usuarios')

    try:
        usuario.delete()
    except ProtectedError:
        messages.error(
            request,
            'No se puede eliminar este usuario porque tiene registros relacionados '
            '(reclamaciones internas, liberaciones o scrap). Puedes editarlo y '
            'desactivarlo para conservar el historial.'
        )
        return redirect('usuarios')

    messages.success(request, 'Usuario eliminado correctamente.')
    return redirect('usuarios')



def axes_lockout(request, credentials=None):
    messages.error(
        request,
        'Demasiados intentos fallidos. Tu acceso fue bloqueado temporalmente por 10 minutos.'
    )
    return redirect('login')