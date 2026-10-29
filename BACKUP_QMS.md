# Respaldos de QMS

## Objetivo

QMS mantiene una copia local y una copia remota de la base de datos y de los archivos multimedia.

La copia remota se almacena en el servidor Windows de la empresa, en:

```text
P:\16 T.I\09 QMS BACKUP
```

En Linux esa unidad se accede mediante el recurso SMB:

```text
\\192.168.1.68\vcl general\16 T.I\09 QMS BACKUP
```

La aplicación Django no ejecuta el respaldo desde `views.py`. El respaldo se ejecuta desde un script del servidor y se programa con `cron`.

El proceso automático **nunca restaura información**. Solo crea el respaldo, copia los archivos al servidor Windows y valida que el archivo de base de datos sea legible. La restauración únicamente se realiza manualmente cuando sea necesario.

## Significado de VCL_TEST

El nombre actual de la base y de los servicios conserva la denominación `VCL_TEST`. En la documentación de QMS, `TEST` se interpreta como una sigla institucional:

**Technology, Engineering, Systems and Traceability**.

Por lo tanto, `VCL_TEST` significa **VCL Technology, Engineering, Systems and Traceability**. No identifica un ambiente de pruebas; corresponde al sistema productivo actual. El nombre técnico se conserva para evitar cambios innecesarios en Docker, variables de entorno y conexiones existentes.

## Estructura de los respaldos

Cada ejecución genera una carpeta con fecha y hora:

```text
qms_YYYYMMDD_HHMMSS/
├── database.dump
├── database.dump.sha256
└── media/
```

Ejemplo:

```text
qms_20261028_111138/
├── database.dump
├── database.dump.sha256
└── media/
```

## Requisitos

- Servidor Linux de QMS en `/home/qms/SGC`.
- Docker Compose funcionando.
- Servicio de base de datos llamado `db_vcl_test`.
- Contenedor de aplicación llamado `vcl_test`.
- Servidor Windows accesible en `192.168.1.68`.
- Recurso SMB compartido llamado `vcl general`.
- Usuario de Windows con permisos de lectura y escritura.

## Configuración en Windows

La unidad `P:` corresponde al recurso remoto:

```text
\\192.168.1.68\vcl general
```

La carpeta de respaldos debe estar disponible en:

```text
P:\16 T.I\09 QMS BACKUP
```

El usuario usado por Linux debe tener permisos de escritura tanto en los permisos del recurso compartido como en los permisos NTFS de la carpeta.

## Montaje SMB en Linux

Instalar el soporte SMB:

```bash
sudo apt update
sudo apt install -y cifs-utils
```

Crear el punto de montaje:

```bash
sudo mkdir -p /mnt/qms-backups
```

Crear el archivo de credenciales:

```bash
sudo nano /root/.qms-smb-credentials
```

Contenido:

```text
username=qms_backup
password=4dm1nvc1+26
```

Proteger el archivo:

```bash
sudo chmod 600 /root/.qms-smb-credentials
```

Montar el recurso:

```bash
sudo mount -t cifs "//192.168.1.68/vcl general" /mnt/qms-backups \
  -o credentials=/root/.qms-smb-credentials,vers=3.0,sec=ntlmssp,uid=1000,gid=1000,dir_mode=0770,file_mode=0660
```

El `uid` y `gid` deben corresponder al usuario `qms`. Se pueden consultar con:

```bash
id qms
```

Verificar el acceso:

```bash
ls -la "/mnt/qms-backups/16 T.I/09 QMS BACKUP"
touch "/mnt/qms-backups/16 T.I/09 QMS BACKUP/prueba_backup.txt"
rm "/mnt/qms-backups/16 T.I/09 QMS BACKUP/prueba_backup.txt"
```

## Montaje automático después de reiniciar

Editar `/etc/fstab`:

```bash
sudo nano /etc/fstab
```

Agregar una línea como esta, ajustando `uid` y `gid` si es necesario:

```text
//192.168.1.68/vcl\040general /mnt/qms-backups cifs credentials=/root/.qms-smb-credentials,vers=3.0,sec=ntlmssp,uid=1000,gid=1000,dir_mode=0770,file_mode=0660,_netdev,nofail 0 0
```

Probar la configuración:

```bash
sudo umount /mnt/qms-backups
sudo mount -a
ls -la "/mnt/qms-backups/16 T.I/09 QMS BACKUP"
```

## Script de respaldo

Ubicación:

```text
/home/qms/SGC/scripts/backup_qms.sh
```

Contenido recomendado:

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="/home/qms/SGC"
LOCAL_ROOT="$PROJECT_DIR/backups"
REMOTE_ROOT="/mnt/qms-backups/16 T.I/09 QMS BACKUP"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
LOCAL_BACKUP="$LOCAL_ROOT/qms_$TIMESTAMP"
REMOTE_BACKUP="$REMOTE_ROOT/qms_$TIMESTAMP"

cd "$PROJECT_DIR"
mkdir -p "$LOCAL_BACKUP"

echo "Creando respaldo de PostgreSQL..."
docker compose exec -T db_vcl_test sh -c \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
  > "$LOCAL_BACKUP/database.dump"

echo "Copiando media..."
docker compose cp vcl_test:/app/media "$LOCAL_BACKUP/media"

echo "Validando base de datos..."
docker compose cp "$LOCAL_BACKUP/database.dump" \
  db_vcl_test:/tmp/qms_database.dump
docker compose exec -T db_vcl_test \
  pg_restore --list /tmp/qms_database.dump > /dev/null
docker compose exec -T db_vcl_test \
  rm -f /tmp/qms_database.dump

if ! mountpoint -q /mnt/qms-backups; then
    echo "ERROR: el servidor Windows no está montado"
    exit 1
fi

echo "Copiando respaldo al servidor Windows..."
mkdir -p "$REMOTE_BACKUP"
cp -a "$LOCAL_BACKUP/database.dump" "$REMOTE_BACKUP/"
cp -a "$LOCAL_BACKUP/media" "$REMOTE_BACKUP/"
sha256sum "$REMOTE_BACKUP/database.dump" \
  > "$REMOTE_BACKUP/database.dump.sha256"

echo "Respaldo completado:"
echo "Local:  $LOCAL_BACKUP"
echo "Remoto: $REMOTE_BACKUP"
du -sh "$LOCAL_BACKUP"
du -sh "$REMOTE_BACKUP"
```

Dar permisos de ejecución:

```bash
chmod u+x /home/qms/SGC/scripts/backup_qms.sh
```

Ejecutar manualmente:

```bash
cd /home/qms/SGC
./scripts/backup_qms.sh
```

## Programación automática

Editar el cron del usuario `qms`:

```bash
crontab -e
```

Ejecutar todos los días a las 02:00:

```cron
0 2 * * * /home/qms/SGC/scripts/backup_qms.sh >> /home/qms/SGC/backups/backup.log 2>&1
```

Consultar el registro:

```bash
tail -50 /home/qms/SGC/backups/backup.log
```

## Validación de integridad

Buscar el archivo de checksum:

```bash
find "/mnt/qms-backups/16 T.I/09 QMS BACKUP" \
  -name "database.dump.sha256" -print
```

Validar el archivo usando la ruta encontrada:

```bash
sha256sum -c "/mnt/qms-backups/16 T.I/09 QMS BACKUP/qms_YYYYMMDD_HHMMSS/database.dump.sha256"
```

Resultado esperado:

```text
database.dump: OK
```

No se debe escribir en la terminal el prompt `qms@qms:~/SGC$`; ese texto solo identifica la terminal.

## Restauración manual de la base de datos

La restauración no forma parte del proceso automático. Solo debe ejecutarse si es necesario recuperar QMS después de una falla o pérdida de información. El `cron` nunca restaura datos.

Ejemplo de respaldo disponible en Windows:

```text
P:\16 T.I\09 QMS BACKUP\qms_20261028_111415\
├── database.dump
├── database.dump.sha256
└── media\
```

### 1. Seleccionar y validar el respaldo

En Linux, la unidad Windows está montada en `/mnt/qms-backups`:

```bash
BACKUP_DIR="/mnt/qms-backups/16 T.I/09 QMS BACKUP/qms_20261028_111415"
sha256sum -c "$BACKUP_DIR/database.dump.sha256"
```

El resultado esperado es:

```text
database.dump: OK
```

El archivo `.sha256` solo verifica la integridad. El archivo que se restaura es `database.dump`.

### 2. Crear un respaldo del estado actual

Antes de sobrescribir la base de datos, crear un respaldo nuevo:

```bash
cd /home/qms/SGC
./scripts/backup_qms.sh
```

### 3. Copiar el respaldo al contenedor

```bash
docker compose cp \
  "$BACKUP_DIR/database.dump" \
  db_vcl_test:/tmp/qms_restore.dump
```

### 4. Detener temporalmente la aplicación

```bash
docker compose stop vcl_test
```

### 5. Restaurar la base de datos

La opción `--clean` elimina los objetos actuales antes de restaurarlos. Ejecutar este comando únicamente después de confirmar que el respaldo es el correcto:

```bash
docker compose exec -T db_vcl_test sh -c \
'pg_restore --clean --if-exists --no-owner --exit-on-error \
-U "$POSTGRES_USER" \
-d "$POSTGRES_DB" \
/tmp/qms_restore.dump'
```

### 6. Iniciar nuevamente QMS

```bash
docker compose start vcl_test
```

### 7. Eliminar el archivo temporal

```bash
docker compose exec -T db_vcl_test \
  rm -f /tmp/qms_restore.dump
```

La restauración es una operación manual y potencialmente destructiva. Debe realizarse con cuidado, preferentemente durante una ventana de mantenimiento.

## Errores comunes

### `Permiso denegado` al ejecutar el script

```bash
chmod u+x /home/qms/SGC/scripts/backup_qms.sh
```

También se puede ejecutar con:

```bash
bash /home/qms/SGC/scripts/backup_qms.sh
```

### `mkdir: Permission denied` en la carpeta Windows

El recurso SMB se montó como `root` o el usuario Windows no tiene permiso de escritura. Desmontar y volver a montar usando `uid`, `gid`, `dir_mode` y `file_mode`, como se indica arriba.

### `pg_restore` no existe en Linux

La validación se ejecuta dentro del contenedor PostgreSQL:

```bash
docker compose exec -T db_vcl_test pg_restore --list /tmp/qms_database.dump
```

No es obligatorio instalar el cliente PostgreSQL en el sistema Linux.

### Error al crear defectos de Scrap después de una restauración

Si la secuencia de PostgreSQL quedó desfasada, revisar y corregirla:

```bash
docker compose exec -T db_vcl_test sh -c \
'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
"SELECT setval(\n+  '\''defectos_scrap_id_defecto_scrap_seq'\'',\n+  (SELECT MAX(id_defecto_scrap) FROM defectos_scrap),\n+  true\n+);"'
```

Esto asegura que el siguiente defecto use un ID posterior al máximo existente.

## Politica de retencion por niveles

Para evitar guardar varias copias fisicas de la misma informacion, el respaldo
debe pasar entre niveles mediante `mv` despues de validar correctamente el
archivo:

```text
backups/
├── diario/     # hasta 7 respaldos recientes
├── semanal/    # 1 respaldo por semana, conservar 4
└── mensual/    # 1 respaldo por mes, conservar 12
```

El script debe usar estas rutas:

```bash
LOCAL_DAILY="$PROJECT_DIR/backups/diario"
LOCAL_WEEKLY="$PROJECT_DIR/backups/semanal"
LOCAL_MONTHLY="$PROJECT_DIR/backups/mensual"

REMOTE_DAILY="$REMOTE_ROOT/diario"
REMOTE_WEEKLY="$REMOTE_ROOT/semanal"
REMOTE_MONTHLY="$REMOTE_ROOT/mensual"

mkdir -p "$LOCAL_DAILY" "$LOCAL_WEEKLY" "$LOCAL_MONTHLY"
mkdir -p "$REMOTE_DAILY" "$REMOTE_WEEKLY" "$REMOTE_MONTHLY"
```

El respaldo nuevo se crea en `diario` con un nombre como:

```text
qms_D_20261029_020000
```

Al finalizar cada semana, el respaldo diario mas reciente se mueve a `semanal`
y se renombra con el numero de semana, por ejemplo:

```text
qms_W_2026-W44_20261029_020000
```

Al finalizar cada mes, el respaldo semanal mas reciente se mueve a `mensual` y
se renombra, por ejemplo:

```text
qms_M_2026-10_20261029_020000
```

Despues de cada movimiento se conserva solamente lo siguiente:

```text
diario/   -> los ultimos 7 respaldos
semanal/  -> los ultimos 4 respaldos semanales
mensual/  -> los ultimos 12 respaldos mensuales
```

Los respaldos deben eliminarse unicamente despues de confirmar que el nuevo
respaldo fue creado, copiado y validado correctamente.

## Recomendaciones
- Mantener la copia local y la copia del servidor Windows.
- Probar periódicamente la restauración de un respaldo.
- No compartir el archivo `/root/.qms-smb-credentials`.
- Mantener al menos 30 días de respaldos si el espacio disponible lo permite.
- Revisar periódicamente `backup.log`.
