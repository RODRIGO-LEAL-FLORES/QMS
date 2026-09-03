# Imagen base
FROM python:3.13-slim

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Crear usuario y grupo sin privilegios
RUN addgroup --system django && \
    adduser --system --ingroup django django

# Directorio de trabajo
WORKDIR /app

# Dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*s

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar proyecto
COPY . .

# Recolectar archivos estáticos para que WhiteNoise los sirva en producción
RUN python manage.py collectstatic --noinput

# Dar permisos al usuario django
RUN chown -R django:django /app

# Ejecutar como usuario sin privilegios
USER django

# Puerto de Gunicorn
EXPOSE 8000

# Ejecutar Django
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]