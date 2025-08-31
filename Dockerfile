FROM python:3.12

ENV DEBIAN_FRONTEND=noninteractive \
	PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	PGDATA=/var/lib/postgresql/data

RUN apt-get update && apt-get install -y --no-install-recommends \
	postgresql postgresql-client supervisor ca-certificates tzdata \
  && rm -rf /var/lib/apt/lists/*
#Instalacion de nginx
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql postgresql-client supervisor ca-certificates tzdata nginx \
    && rm -rf /var/lib/apt/lists/*
# Crea directorios de trabajo y datos
WORKDIR /app
RUN mkdir -p /var/lib/postgresql/data && \
	chown -R postgres:postgres /var/lib/postgresql

# Instala dependencias Python y psycopg
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel && \
	pip install "psycopg[binary]>=3.1" && \
	pip install -r /app/requirements.txt

# Copia el código fuente
COPY . /app

# Copia la configuración de Nginx
COPY nginx.conf /etc/nginx/nginx.conf

# Expone puertos para web, postgres y nginx
EXPOSE 8000 5432 80

# Volumen para persistencia de datos de PostgreSQL
VOLUME ["/var/lib/postgresql/data"]

# Arranca Gunicorn y Nginx juntos (simple, para demo/producción básica)
CMD service nginx start && gunicorn -c gunicorn.conf.py global_exchange.wsgi