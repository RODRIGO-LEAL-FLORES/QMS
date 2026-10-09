from django.db import migrations, models


CLIENTES_ACTIVOS = [
    'ALLIED MOTION - GLOBE MOTORS',
    'AMETEK',
    'ARTURO HERNANDEZ',
    'BASLER',
    'BASLER*',
    'BERGSTROM',
    'BLACK & DECKER',
    'BODINE',
    'EATON',
    'EATON-UBUNGANI',
    'ERMCO',
    'HUBBELL',
    'ISA',
    'KATO',
    'KOBLENZ',
    'LHS -ROSS DECCO',
    'LHS-ABB',
    'LHS-AEE',
    'LHS-ALTRAN',
    'LHS-AMP LINE',
    'LHS-ANKO',
    'LHS-CONTROL TRANSFORMERS',
    'LHS-EATON',
    'LHS-EMERSON',
    'LHS-FOSTER TRANSFORMER',
    'LHS-GENERAL TRANSFORMER',
    'LHS-GROSSCHOP',
    'LHS-HITACHI',
    'LHS-HUBBELL',
    'LHS-IMPERIUM',
    'LHS-IPS',
    'LHS-KATO',
    'LHS-MACRO MAGNETICS',
    'LHS-MICRON',
    'LHS-NORLAKE',
    'LHS-NOVA MAGNETICS',
    'LHS-OLSUN',
    'LHS-OLYMPIC',
    'LHS-PACIFIC T.',
    'LHS-POWERTRAN',
    'LHS-QUALITY TRANSFORMER',
    'LHS-SCHNEIDER',
    'LHS-SHAPE',
    'LHS-SOUTHWEST',
    'LHS-SPECIALTY MAGNETICS',
    'LHS-SUNBELT SOLOMON',
    'LHS-SYNERGY MAGNETICS',
    'LHS-TCI',
    'LHS-TRANSFORMER TECH',
    'LHS-WALLACE ELECTRICAL SYS',
    'LITTELFUSE',
    'M&G',
    'MAFESA',
    'MARTIN ENGINEERING',
    'MTE',
    'McMILLAN',
    'NIDEC LEROY SOMER-REYNOSA',
    'PITTMAN',
    'SCHUMACHER',
    'SNC',
    'SOUTHWEST',
    'TURMIX',
    'WEG US',
    'WEG US - RAE',
]


def activar_catalogo_vigente(apps, schema_editor):
    Cliente = apps.get_model('clientes', 'Cliente')
    db_alias = schema_editor.connection.alias
    clientes = Cliente.objects.using(db_alias)

    clientes.update(activo=False)
    for nombre in CLIENTES_ACTIVOS:
        encontrados = clientes.filter(nombre=nombre)
        if encontrados.exists():
            encontrados.update(activo=True)
        else:
            clientes.create(nombre=nombre, activo=True)


def reactivar_clientes(apps, schema_editor):
    Cliente = apps.get_model('clientes', 'Cliente')
    Cliente.objects.using(schema_editor.connection.alias).update(activo=True)


class Migration(migrations.Migration):

    dependencies = [
        ('clientes', '0002_cargar_clientes'),
    ]

    operations = [
        migrations.AddField(
            model_name='cliente',
            name='activo',
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(
            activar_catalogo_vigente,
            reactivar_clientes
        ),
    ]
