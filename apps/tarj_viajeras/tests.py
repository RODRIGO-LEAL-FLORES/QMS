from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, SimpleTestCase, TestCase

from . import views
from .models import (
    ConfiguracionPiezasAlambre,
    Espesor,
    NumeroParteCliente,
    Produccion,
    ReasignacionTarjeta,
    StatusTar,
    TarjetaViajera,
)
from apps.clientes.models import Cliente
from apps.liberaciones.models import TipoLaminacion
from apps.scrap.models import TipoAcero
from .views import (
    usuario_puede_actualizar_datos_tarj_viajeras,
    usuario_puede_actualizar_tarj_viajeras,
    usuario_puede_gestionar_tarj_viajeras,
    usuario_puede_imprimir_tarj_viajeras,
    usuario_puede_ver_tarj_viajeras,
)


class PermisosTarjetasViajerasTests(SimpleTestCase):
    def setUp(self):
        self.request_factory = RequestFactory()

    def usuario(self, rol_id, **overrides):
        atributos = {
            'is_authenticated': True,
            'is_active': True,
            'puede_gestionar_targetas_viajeras': True,
            'rol_id': rol_id,
        }
        atributos.update(overrides)
        return SimpleNamespace(**atributos)

    def test_admin_y_encargado_tienen_gestion_completa(self):
        for rol_id in (1, 2):
            with self.subTest(rol_id=rol_id):
                usuario = self.usuario(rol_id)
                self.assertTrue(usuario_puede_gestionar_tarj_viajeras(usuario))
                self.assertTrue(usuario_puede_imprimir_tarj_viajeras(usuario))
                self.assertTrue(
                    usuario_puede_actualizar_datos_tarj_viajeras(usuario)
                )

    def test_usuario_general_puede_imprimir_y_actualizar_datos(self):
        usuario = self.usuario(3)

        self.assertTrue(usuario_puede_ver_tarj_viajeras(usuario))
        self.assertTrue(usuario_puede_imprimir_tarj_viajeras(usuario))
        self.assertTrue(usuario_puede_actualizar_tarj_viajeras(usuario))
        self.assertTrue(usuario_puede_actualizar_datos_tarj_viajeras(usuario))
        self.assertFalse(usuario_puede_gestionar_tarj_viajeras(usuario))

    def test_auditor_solo_puede_actualizar_estatus(self):
        usuario = self.usuario(4)

        self.assertTrue(usuario_puede_ver_tarj_viajeras(usuario))
        self.assertTrue(usuario_puede_actualizar_tarj_viajeras(usuario))
        self.assertFalse(usuario_puede_imprimir_tarj_viajeras(usuario))
        self.assertFalse(usuario_puede_actualizar_datos_tarj_viajeras(usuario))
        self.assertFalse(usuario_puede_gestionar_tarj_viajeras(usuario))

    def test_usuarios_sin_acceso_al_modulo_no_tienen_permisos(self):
        usuario = self.usuario(3, puede_gestionar_targetas_viajeras=False)

        self.assertFalse(usuario_puede_ver_tarj_viajeras(usuario))
        self.assertFalse(usuario_puede_imprimir_tarj_viajeras(usuario))
        self.assertFalse(usuario_puede_actualizar_tarj_viajeras(usuario))

    def editar_tarjeta(self, rol_id, datos):
        tarjeta = SimpleNamespace(
            numero_tarjeta=5,
            sufijo=None,
            status=SimpleNamespace(pk=1),
            numero_alambres=75,
            piezas_por_alambre=100,
            peso_kg='536.00',
            peso_lbs='1181.68',
            tara='10',
            save=Mock(),
        )
        nuevo_status = SimpleNamespace(pk=2)
        request = self.request_factory.post('/tarjetas/editar/1/', datos)
        request.user = self.usuario(rol_id)
        request.session = {}
        request._messages = FallbackStorage(request)

        def obtener_objeto(modelo, **kwargs):
            return nuevo_status if modelo is StatusTar else tarjeta

        with patch.object(views, 'get_object_or_404', side_effect=obtener_objeto):
            response = views.tarjeta_viajera_editar(request, item_id=1)

        self.assertEqual(response.status_code, 302)
        return tarjeta, nuevo_status

    def test_usuario_general_no_puede_cambiar_folio_ni_sufijo(self):
        tarjeta, nuevo_status = self.editar_tarjeta(3, {
            'numero_tarjeta': '9000',
            'sufijo': 'Z',
            'id_status': '2',
            'numero_alambres': '80',
            'piezas_por_alambre': '110',
            'peso_kg': '540.00',
            'peso_lbs': '1190.50',
            'tara': '12',
        })

        self.assertEqual(tarjeta.numero_tarjeta, 5)
        self.assertIsNone(tarjeta.sufijo)
        self.assertIs(tarjeta.status, nuevo_status)
        self.assertEqual(tarjeta.numero_alambres, '80')
        self.assertEqual(tarjeta.piezas_por_alambre, '110')
        self.assertEqual(tarjeta.peso_kg, '540.00')
        self.assertEqual(tarjeta.peso_lbs, '1190.50')
        self.assertEqual(tarjeta.tara, '12')

    def test_auditor_no_puede_actualizar_datos_fuera_del_estatus(self):
        tarjeta, nuevo_status = self.editar_tarjeta(4, {
            'numero_tarjeta': '9000',
            'sufijo': 'Z',
            'id_status': '2',
            'numero_alambres': '80',
            'piezas_por_alambre': '110',
            'peso_kg': '540.00',
            'peso_lbs': '1190.50',
            'tara': '12',
        })

        self.assertEqual(tarjeta.numero_tarjeta, 5)
        self.assertIsNone(tarjeta.sufijo)
        self.assertIs(tarjeta.status, nuevo_status)
        self.assertEqual(tarjeta.numero_alambres, 75)
        self.assertEqual(tarjeta.piezas_por_alambre, 100)
        self.assertEqual(tarjeta.peso_kg, '536.00')
        self.assertEqual(tarjeta.peso_lbs, '1181.68')
        self.assertEqual(tarjeta.tara, '10')
        tarjeta.save.assert_called_once_with(update_fields=['status'])


class ConfiguracionPiezasAlambreTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(nombre='Cliente prueba')
        self.numero_parte = NumeroParteCliente.objects.create(
            descripcion='Parte prueba'
        )
        self.laminacion = TipoLaminacion.objects.create(
            especificacion='Laminacion prueba'
        )
        self.material = TipoAcero.objects.create(especificacion='Acero prueba')
        self.espesor = Espesor.objects.create(espesor='1.00')
        self.usuario = SimpleNamespace(
            is_authenticated=True,
            is_active=True,
            puede_gestionar_targetas_viajeras=True,
            rol_id=1,
        )

    def post(self, path, view, data, user=None, **kwargs):
        request = RequestFactory().post(path, data)
        request.user = user or self.usuario
        request.session = {}
        request._messages = FallbackStorage(request)
        return view(request, **kwargs)

    def test_crear_configuracion_y_usarla_en_produccion_y_tarjetas(self):
        response = self.post(
            '/catalogos/piezas-por-alambre/crear/',
            views.configuracion_piezas_alambre_crear,
            {
                'cliente': str(self.cliente.pk),
                'numero_parte_cliente': str(self.numero_parte.pk),
                'laminacion': str(self.laminacion.pk),
                'proceso': 'R',
                'piezas_por_alambre': '120',
            },
        )
        self.assertEqual(response.status_code, 302)
        configuracion = ConfiguracionPiezasAlambre.objects.get()
        self.assertEqual(configuracion.piezas_por_alambre, 120)

        response = self.post(
            '/produccion/crear/',
            views.produccion_crear,
            {
                'numero_orden_trabajo': '4949',
                'proceso': 'R',
                'lote': 'LOTE-TEST',
                'numero_orden_compra': '',
                'id_cliente': str(self.cliente.pk),
                'id_material': str(self.material.pk),
                'id_espesor': str(self.espesor.pk),
                'id_laminacion': str(self.laminacion.pk),
                'id_num_pcli': str(self.numero_parte.pk),
            },
        )
        self.assertEqual(response.status_code, 302)
        produccion = Produccion.objects.get()
        self.assertEqual(produccion.numero_orden_trabajo, 'R:4949')
        self.assertEqual(produccion.proceso, 'R')
        self.assertEqual(produccion.piezas_por_alambre, 120)

        status = StatusTar.objects.create(descripcion='CREADA')
        response = self.post(
            f'/tarjetas/crear/{produccion.pk}/',
            views.tarjeta_viajera_crear,
            {
                'cantidad_tarjetas': '1',
                'sufijo': '',
                'numero_alambres': '4',
                'piezas_por_alambre': '999',
                'peso_kg': '',
                'peso_lbs': '',
                'tara': '',
            },
            produccion_id=produccion.pk,
        )
        self.assertEqual(response.status_code, 302)
        tarjeta = TarjetaViajera.objects.get(status=status)
        self.assertEqual(tarjeta.piezas_por_alambre, 120)

    def test_no_crea_orden_si_falta_la_relacion_del_proceso(self):
        response = self.post(
            '/produccion/crear/',
            views.produccion_crear,
            {
                'numero_orden_trabajo': '4950',
                'proceso': 'E',
                'lote': 'LOTE-TEST',
                'numero_orden_compra': '',
                'id_cliente': str(self.cliente.pk),
                'id_material': str(self.material.pk),
                'id_espesor': str(self.espesor.pk),
                'id_laminacion': str(self.laminacion.pk),
                'id_num_pcli': str(self.numero_parte.pk),
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Produccion.objects.exists())

    def test_numero_orden_se_prefija_sin_repetir_prefijo(self):
        for proceso, numero_enviado, esperado in (
            ('R', '4949', 'R:4949'),
            ('EI', 'EI:4951', 'EI:4951'),
            ('CTL', 'R:4953', 'CTL:4953'),
        ):
            with self.subTest(proceso=proceso):
                request = RequestFactory().post(
                    '/produccion/crear/',
                    {
                        'numero_orden_trabajo': numero_enviado,
                        'proceso': proceso,
                    },
                )
                datos = views._datos_produccion(request)
                self.assertEqual(datos['numero_orden'], esperado)

    def test_separar_codigo_acepta_variaciones_del_lector(self):
        codigos_validos = (
            ('R:9646|1', ('R:9646', 1, None)),
            ('R:9646Ç1\r\n', ('R:9646', 1, None)),
            ('R:9646:1', ('R:9646', 1, None)),
            (']C1R:9646¦1-A', ('R:9646', 1, 'A')),
            ('1', (None, 1, None)),
        )

        for codigo, esperado in codigos_validos:
            with self.subTest(codigo=codigo):
                self.assertEqual(
                    views._separar_codigo_tarjeta(codigo),
                    esperado
                )

    def test_pantalla_de_relaciones_se_renderiza(self):
        request = RequestFactory().get('/catalogos/piezas-por-alambre/')
        request.user = self.usuario

        response = views.configuracion_piezas_alambre(request)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Configuración de piezas por alambre')

    def test_usuario_general_actualiza_tarjeta_por_codigo_con_prefijo_y_sufijo(self):
        status_anterior = StatusTar.objects.create(
            descripcion='Pendiente'
        )
        status_nuevo = StatusTar.objects.create(
            descripcion='Terminada'
        )
        produccion = Produccion.objects.create(
            numero_orden_trabajo='R:4949',
            proceso='R',
            lote='LOTE-TEST',
            cliente=self.cliente,
            material=self.material,
            espesor=self.espesor,
            laminacion=self.laminacion,
            numero_parte_cliente=self.numero_parte,
        )
        tarjeta = TarjetaViajera.objects.create(
            produccion=produccion,
            numero_tarjeta=1,
            sufijo='A',
            status=status_anterior,
        )
        usuario_general = SimpleNamespace(
            is_authenticated=True,
            is_active=True,
            puede_gestionar_targetas_viajeras=True,
            rol_id=3,
        )

        response = self.post(
            '/tarjetas/escaner/cambiar-status/',
            views.cambiar_status_barcode,
            {
                'tarjeta': 'RÑ4949Ç1-A',
                'status': str(status_nuevo.pk),
            },
            user=usuario_general,
        )

        self.assertEqual(response.status_code, 302)
        tarjeta.refresh_from_db()
        self.assertEqual(tarjeta.status_id, status_nuevo.pk)

    def test_usuario_general_y_auditor_actualizan_codigo_de_captura(self):
        status_anterior = StatusTar.objects.create(
            descripcion='Pendiente'
        )
        status_nuevo = StatusTar.objects.create(
            descripcion='Terminada'
        )
        produccion = Produccion.objects.create(
            numero_orden_trabajo='R:9646',
            proceso='R',
            lote='LOTE-TEST',
            cliente=self.cliente,
            material=self.material,
            espesor=self.espesor,
            laminacion=self.laminacion,
            numero_parte_cliente=self.numero_parte,
        )

        for rol_id, numero_tarjeta in ((3, 1), (4, 2)):
            with self.subTest(rol_id=rol_id):
                tarjeta = TarjetaViajera.objects.create(
                    produccion=produccion,
                    numero_tarjeta=numero_tarjeta,
                    status=status_anterior,
                )
                usuario = SimpleNamespace(
                    is_authenticated=True,
                    is_active=True,
                    puede_gestionar_targetas_viajeras=True,
                    rol_id=rol_id,
                )

                response = self.post(
                    '/tarjetas/escaner/cambiar-status/',
                    views.cambiar_status_barcode,
                    {
                        'tarjeta': f'R:9646|{numero_tarjeta}',
                        'status': str(status_nuevo.pk),
                    },
                    user=usuario,
                )

                self.assertEqual(response.status_code, 302)
                tarjeta.refresh_from_db()
                self.assertEqual(tarjeta.status_id, status_nuevo.pk)

    def test_usuario_general_y_auditor_actualizan_con_barcode_solo_folio(self):
        status_anterior = StatusTar.objects.create(
            descripcion='Pendiente'
        )
        status_nuevo = StatusTar.objects.create(
            descripcion='Terminada'
        )
        produccion = Produccion.objects.create(
            numero_orden_trabajo='R:9646',
            proceso='R',
            lote='LOTE-TEST',
            cliente=self.cliente,
            material=self.material,
            espesor=self.espesor,
            laminacion=self.laminacion,
            numero_parte_cliente=self.numero_parte,
        )

        for rol_id, numero_tarjeta in ((3, 3), (4, 4)):
            with self.subTest(rol_id=rol_id):
                tarjeta = TarjetaViajera.objects.create(
                    produccion=produccion,
                    numero_tarjeta=numero_tarjeta,
                    status=status_anterior,
                )
                usuario = SimpleNamespace(
                    is_authenticated=True,
                    is_active=True,
                    puede_gestionar_targetas_viajeras=True,
                    rol_id=rol_id,
                )

                response = self.post(
                    '/tarjetas/escaner/cambiar-status/',
                    views.cambiar_status_barcode,
                    {
                        'tarjeta': str(numero_tarjeta),
                        'status': str(status_nuevo.pk),
                    },
                    user=usuario,
                )

                self.assertEqual(response.status_code, 302)
                tarjeta.refresh_from_db()
                self.assertEqual(tarjeta.status_id, status_nuevo.pk)

    def test_error_distingue_codigo_de_estatus_invalido(self):
        status = StatusTar.objects.create(descripcion='Pendiente')
        produccion = Produccion.objects.create(
            numero_orden_trabajo='R:9646',
            proceso='R',
            lote='LOTE-TEST',
            cliente=self.cliente,
            material=self.material,
            espesor=self.espesor,
            laminacion=self.laminacion,
            numero_parte_cliente=self.numero_parte,
        )
        tarjeta = TarjetaViajera.objects.create(
            produccion=produccion,
            numero_tarjeta=1,
            status=status,
        )

        request = RequestFactory().post(
            '/tarjetas/escaner/cambiar-status/',
            {'tarjeta': 'R:9646|1', 'status': 'no-numerico'},
        )
        request.user = self.usuario
        request.session = {}
        request._messages = FallbackStorage(request)

        response = views.cambiar_status_barcode(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            list(request._messages)[0].message,
            'El código de estatus debe ser numérico. Escanea primero la '
            'tarjeta y después el código del estatus.'
        )
        tarjeta.refresh_from_db()
        self.assertEqual(tarjeta.status_id, status.pk)


class ReasignacionTarjetasTests(TestCase):
    def setUp(self):
        self.cliente_origen = Cliente.objects.create(nombre='Cliente origen')
        self.cliente_destino = Cliente.objects.create(nombre='Cliente destino')
        self.cliente_otro_destino = Cliente.objects.create(
            nombre='Otro cliente destino'
        )
        self.numero_parte_origen = NumeroParteCliente.objects.create(
            descripcion='Parte origen'
        )
        self.numero_parte_destino = NumeroParteCliente.objects.create(
            descripcion='Parte destino'
        )
        self.numero_parte_otro_destino = NumeroParteCliente.objects.create(
            descripcion='Otra parte destino'
        )
        material = TipoAcero.objects.create(especificacion='Acero prueba')
        espesor = Espesor.objects.create(espesor='1.00')
        laminacion = TipoLaminacion.objects.create(
            especificacion='Laminacion prueba'
        )
        self.status = StatusTar.objects.create(descripcion='Pendiente')
        self.produccion = Produccion.objects.create(
            numero_orden_trabajo='OT-TEST',
            lote='LOTE-TEST',
            numero_orden_compra='OC-TEST',
            cliente=self.cliente_origen,
            material=material,
            espesor=espesor,
            laminacion=laminacion,
            numero_parte_cliente=self.numero_parte_origen
        )
        self.tarjetas = [
            TarjetaViajera.objects.create(
                produccion=self.produccion,
                numero_tarjeta=numero,
                status=self.status
            )
            for numero in range(1, 8)
        ]

    def _reasignar(self, tarjeta, ids, cliente, numero_parte):
        request = RequestFactory().post(
            f'/tarjetas/reasignar/{tarjeta.pk}/crear/',
            {
                'tarjetas': [str(tarjeta_id) for tarjeta_id in ids],
                'id_cliente': str(cliente.pk),
                'id_num_pcli': str(numero_parte.pk),
                'motivo': 'Cambio solicitado'
            }
        )
        request.user = SimpleNamespace(
            is_authenticated=True,
            is_active=True,
            puede_gestionar_targetas_viajeras=True,
            rol_id=1
        )
        request.session = {}
        request._messages = FallbackStorage(request)

        return views.tarjeta_viajera_reasignar_crear(
            request,
            item_id=tarjeta.pk
        )

    def test_tarjeta_omitida_se_agrega_a_variante_existente(self):
        primera, segunda = self.tarjetas[:2]
        self._reasignar(
            primera,
            [primera.pk],
            self.cliente_destino,
            self.numero_parte_destino
        )
        primera.refresh_from_db()
        variante_creada = primera.produccion
        numero_variantes = Produccion.objects.filter(
            subvariante_de=self.produccion
        ).count()

        request = RequestFactory().post(
            f'/tarjetas/reasignar/{segunda.pk}/crear/',
            {
                'tarjetas': [str(segunda.pk)],
                'id_produccion_destino': str(variante_creada.pk),
                'motivo': 'Agregar tarjeta omitida'
            }
        )
        request.user = SimpleNamespace(
            is_authenticated=True,
            is_active=True,
            puede_gestionar_targetas_viajeras=True,
            rol_id=1
        )
        request.session = {}
        request._messages = FallbackStorage(request)

        response = views.tarjeta_viajera_reasignar_crear(
            request,
            item_id=segunda.pk
        )

        self.assertEqual(response.status_code, 302)
        segunda.refresh_from_db()
        self.assertEqual(segunda.produccion_id, variante_creada.pk)
        self.assertEqual(
            Produccion.objects.filter(
                subvariante_de=self.produccion
            ).count(),
            numero_variantes
        )
        self.assertTrue(
            ReasignacionTarjeta.objects.filter(
                tarjeta=segunda,
                produccion_destino=variante_creada
            ).exists()
        )

    def test_varias_tarjetas_comparten_destino_y_otra_crea_variante_distinta(self):
        primeras_seis = self.tarjetas[:6]
        response = self._reasignar(
            primeras_seis[0],
            [tarjeta.pk for tarjeta in primeras_seis],
            self.cliente_destino,
            self.numero_parte_destino
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            Produccion.objects.filter(
                subvariante_de=self.produccion
            ).count(),
            1
        )
        primeras_seis[0].refresh_from_db()
        destino_compartido = primeras_seis[0].produccion
        for tarjeta in primeras_seis:
            tarjeta.refresh_from_db()
            self.assertEqual(tarjeta.produccion_id, destino_compartido.pk)
        self.assertEqual(
            ReasignacionTarjeta.objects.filter(
                produccion_destino=destino_compartido
            ).count(),
            6
        )

        response = self._reasignar(
            self.tarjetas[6],
            [self.tarjetas[6].pk],
            self.cliente_otro_destino,
            self.numero_parte_otro_destino
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            Produccion.objects.filter(
                subvariante_de=self.produccion
            ).count(),
            2
        )
        self.tarjetas[6].refresh_from_db()
        self.assertNotEqual(
            self.tarjetas[6].produccion_id,
            destino_compartido.pk
        )
        self.assertEqual(
            self.tarjetas[6].produccion.cliente_id,
            self.cliente_otro_destino.pk
        )
