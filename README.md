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

### Base de Datos PostgreSQL

1. **Instalar PostgreSQL**
2. **Crear base de datos:**
   ```sql
   CREATE DATABASE global_exchange;
   CREATE USER global_exchange_user WITH PASSWORD 'tu_password';
   GRANT ALL PRIVILEGES ON DATABASE global_exchange TO global_exchange_user;
   ```

3.  **Actualizar configuración en `global_exchange/settings.py`:**
    
   a. **Abra su archivo `.env`** y descomente las variables de entorno de la base de datos (`DB_*`).
   
   b. **Complete las variables** con los datos de su base de datos PostgreSQL:
   ```
   DB_NAME=global_exchange
   DB_USER=usuario_exchange
   DB_PASSWORD=tu_contraseña
   DB_HOST=localhost
   DB_PORT=5432
   ```
   
   c. En el archivo `settings.py`, asegúrese de que la sección de la base de datos de PostgreSQL esté descomentada para que lea estas variables de su archivo `.env`.

## 📝 Licencia

Este proyecto es para fines académicos.

---

**¡Global Exchange - Digitalizando el futuro de las casas de cambio!** 🚀