# Imagen base con Python 3.12
FROM python:3.12

# Variables de entorno para que Python trabaje bien en Docker
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Establecer directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalar dependencias del sistema necesarias (ej: para psycopg2, Pillow, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    git \
    ca-certificates \
    tzdata \
 && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalarlos primero (mejora el cache de Docker)
COPY requirementsProduccion.txt /app/requirementsProduccion.txt
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r /app/requirementsProduccion.txt

# Copiar el código fuente de la app
COPY . /app

# Recolectar archivos estáticos (para que Nginx pueda servirlos)
#RUN python manage.py collectstatic --noinput

# Exponer puerto de Gunicorn
EXPOSE 8000

# Comando de inicio: Gunicorn como servidor WSGI
CMD ["gunicorn", "-c", "gunicorn.conf.py", "global_exchange.wsgi"]
