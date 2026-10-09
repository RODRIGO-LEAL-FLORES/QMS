from django.db import migrations


CLIENTES = [
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


def cargar_clientes(apps, schema_editor):
    Cliente = apps.get_model('clientes', 'Cliente')

    for nombre in CLIENTES:
        if not Cliente.objects.filter(nombre=nombre).exists():
            Cliente.objects.create(nombre=nombre)


def revertir_clientes(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('clientes', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(cargar_clientes, revertir_clientes),
    ]
