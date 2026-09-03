from django.db import migrations


CLIENTES = [
    'AMETEK',
    'BERGSTROM ',
    'BODINE',
    'KOBLENZ',
    'LAPHAM-ALTRAN',
    'LAPHAM-ANKO',
    'LAPHAM-CENTRAL MOLONEY',
    'LAPHAM-COILTRAN',
    'LAPHAM-CONTROL TRANSFORMERS',
    'LAPHAM-EATON',
    'LAPHAM-EMERSON',
    'LAPHAM-HICKEY',
    'LAPHAM-KATO',
    'LAPHAM-LACONIA',
    'LAPHAM-MACRO MAGNETICS',
    'LAPHAM-MICRON',
    'LAPHAM-OLYMPIC',
    'LAPHAM-PACIFIC T.',
    'LAPHAM-POWER MAGNETICS',
    'LAPHAM-SCHNEIDER',
    'LAPHAM-SHAPE',
    'LAPHAM-SPANG ',
    'LAPHAM-SPECIALTY MAGNETICS',
    'LAPHAM-SYNERGY MAGNETICS',
    'LITTELFUSE',
    'MAFESA',
    'MARTIN ENGINEERING',
    'MTE',
    'MTE - MXL',
    'NORATEL',
    'PITTMAN',
    'SCHUMACHER',
    'SIGNAL',
    'SNC',
    'TURMIX',
    'TYCO',
    'WEG US',
    'WEG US - RAE',
    'HITACHI',
    'ARTURO HERNANDEZ',
    'Groschopp',
    'South West',
    'BASLER',
    'LAPHAM-GENERAL TRANSFORMER',
    'LAPHAM-NOVA MAGNETICS',
    'MC MILLAN',
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
