# Global Exchange - Sistema de Casa de Cambio Digital

Global Exchange es una plataforma web desarrollada en Django que permite digitalizar las operaciones de una casa de cambio, facilitando a los usuarios realizar transacciones de compra y venta de divisas de manera digital con tasas de cambio actualizadas en tiempo real.

## 📋 Características Principales

- **Operaciones de Divisas**: Compra y venta digital de múltiples monedas.
- **Tasas en Tiempo Real**: Integración con APIs externas para tasas actualizadas.
- **Gestión de Clientes**: Categorización por tipo (Minorista, Corporativo, VIP).
- **Transacciones Seguras**: Múltiples métodos de pago y estados de transacción.
- **Sistema de Notificaciones**: Alertas por email y notificaciones en tiempo real.
- **Reportes y Facturación**: Generación de reportes en PDF y Excel.
- **Panel de Administración**: Gestión completa del sistema.
- **Moneda Digital Propia**: Creación y gestión de la moneda digital de la empresa.

### Prerrequisitos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)
- Git

### Instalación

1. **Clonar el repositorio**
   ```bash
   cd global-exchange
   ```

2. **Crear entorno virtual (recomendado)**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

4.  **Configurar variables de entorno**

    El proyecto utiliza un archivo `.env` para gestionar variables sensibles. Se incluye una plantilla llamada `.env.ejemplo` para facilitar la configuración.

    a. **Copie el archivo de ejemplo:**
    ```bash
    cp .env.ejemplo .env
    ```
    b. **Edite el archivo `.env`** y rellene los valores correspondientes. Como mínimo, se recomienda cambiar `SECRET_KEY` para un entorno de producción.

    c. **Configurar el envío de correos (Gmail):** Para que funcionen características como la verificación de email, es necesario configurar las variables `EMAIL_*`. Si utiliza una cuenta de Gmail, debe generar una **"Contraseña de aplicación"**:
    - Primero, asegúrese de tener la **Verificación en dos pasos activada** en su cuenta de Google.
    - Vaya a la página de seguridad de su cuenta de Google: [myaccount.google.com/security](https://myaccount.google.com/security).
    - En la sección "Cómo inicias sesión en Google", haga clic en **Verificación en dos pasos**.
    - Desplácese hasta el final de la página y seleccione **Contraseñas de aplicaciones**.
    - En "Seleccionar la aplicación", elija "Otro (*nombre personalizado*)" y asígnele un nombre (ej. "Django Global Exchange").
    - Haga clic en "Generar". Google le proporcionará una **contraseña de 16 caracteres**.
    - Copie esta contraseña (sin espacios) y péguela en la variable `EMAIL_HOST_PASSWORD` de su archivo `.env`.

5. **Ejecutar migraciones**
   ```bash
   python manage.py migrate
   ```

6. **Inicializar el sistema con datos básicos**
   ```bash
   python manage.py init_system
   ```
   
   Este comando creará:
   - Monedas base (ARS, USD, EUR, BRL, PYG, CLP, UYU, GEX)
   - Tasas de cambio iniciales
   - Categorías de clientes
   - Métodos de pago
   - Plantillas de notificación
   - Usuarios administradores  (admin1/admin1, admin2/admin2)
   - Usuarios de prueba (usuario1/usuario1, usuario2/usuario2, ... , usuario6/usuario6)

### 🎯 Arrancar el Servidor

#### Servidor de Desarrollo

```bash
python manage.py runserver
```

El servidor estará disponible en: http://127.0.0.1:8000/

## 🛠️ Comandos Útiles

### Gestión de Base de Datos

```bash
# Crear migraciones
python manage.py makemigrations

# Aplicar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser
```

## ⚙️ Configuración de Producción

### Todo estara montado en docker

1. **Instalar Docker:**
    Siga las instrucciones oficiales en [https://docs.docker.com/get-docker/](https://docs.docker.com/get-docker/).
2. **Intrucciones luego de la instalación:**
   Ubicarnos en la carpeta del proyecto donde se encuentr el archivo docker-compose.yml. Ejecutar en la terminal:
    ```bash
    docker compose up --build -d
    ```
    Si es la primera vez que lo ejecutas podria tardar un poco ya que descarga las imagenes y crea los contenedores.

    En cuyo caso es la primera vez que lo ejecutas, debes correr las migraciones y el comando init_system, tambien un comando que para los archivos estaticos
    
    ```bash
      docker compose exec web python manage.py makemigrations
      docker compose exec web python manage.py migrate
      docker compose exec web python manage.py init_system
      docker compose exec web python manage.py collectstatic --noinput
    ```
   
    El primer comando crea las migraciones, el segundo aplica las migraciones, el tercero inicializa el sistema con datos basicos y el ultimo comando recopila los archivos estaticos en la carpeta definida en settings.py


3. **Acceder a la aplicación:**
   Abre tu navegador y ve a `http://localhost:8001` o `http://127.0.0.1:8001/` para acceder


4. **Detener los contenedores:**
   ```bash
   docker compose down
   ```
### Tareas asincronas con Celery y Redis
   Para tareas asincronas
   ```bash
   pip install celery redis
   ```
   para correr redis
   ```bash
   redis-server
   ```
   Celery worker
   ```bash
   celery -A global_exchange worker --loglevel=info
   ```
   Celery beat
   ```bash
   celery -A global_exchange beat --loglevel=info
   ```

   ```bash
   global_exchange/
   ├── __init__.py          # Con la importación de Celery
   ├── celery.py           # Configuración centralizada
   ├── settings.py         # Variables de entorno
   └── tu_app/
      ├── tasks.py        # Tareas específicas
      └── models.py       # Modelos con métodos
   ```


## 📚 Generar o Actualizar la Documentación

Para crear o actualizar la documentación en HTML con Sphinx:

```bash
# Limpiar API vieja (si aplica)
   # Windows
   Remove-Item -Recurse -Force docs\source\api\* -ErrorAction Ignore
   # Linux
   rm -rf docs/source/api/*

# Actualizar los archivos de documentación de la API
sphinx-apidoc -o docs/source/api . -f -e -d 2

# Generar la documentación HTML
sphinx-build -b html docs/source docs/build/html
```

La documentación actualizada estará en `docs/_build/html/index.html`.


## 📝 Licencia

Este proyecto es para fines académicos.

---

**¡Global Exchange - Digitalizando el futuro de las casas de cambio!** 🚀