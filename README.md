# Asistente Educativo - FuncionaBD

Aplicación educativa que combina un chatbot inteligente con reconocimiento de imágenes y ejercicios interactivos para ayudar a los usuarios a aprender a leer y escribir de forma divertida e interactiva.

## Características Principales

- **Autenticación de usuarios**: Sistema de registro e inicio de sesión para personalizar la experiencia.
- **Chatbot educativo**: Responde a preguntas sobre letras, palabras y ayuda en el aprendizaje.
- **Reconocimiento de imágenes**: Captura objetos a través de la cámara y aprende a escribir su nombre.
- **Ejercicios interactivos**: Práctica de reconocimiento de letras, deletreo y emparejamiento.
- **Persistencia de datos**: Almacena usuarios y conversaciones en una base de datos PostgreSQL.
- **Procesamiento asíncrono**: Sistema FIFO para operaciones de base de datos no bloqueantes.

## Requisitos Previos

- Python 3.8 o superior
- PostgreSQL 12 o superior
- Navegador web moderno con soporte para cámara web
- Acceso a internet (para APIs externas de reconocimiento)
- Pip (gestor de paquetes de Python)

## Configuración del Proyecto

### 1. Creación de la Base de Datos PostgreSQL

1. Instala PostgreSQL si aún no lo tienes:
   ```bash
   # En sistemas basados en Debian/Ubuntu
   sudo apt-get install postgresql postgresql-contrib
   
   # En macOS con Homebrew
   brew install postgresql
   ```

2. Inicia PostgreSQL y crea una base de datos:
   ```bash
   # Iniciar PostgreSQL (varía según tu sistema)
   sudo service postgresql start  # Linux
   brew services start postgresql  # macOS
   
   # Acceder a la consola de PostgreSQL
   sudo -u postgres psql
   
   # Dentro de la consola de PostgreSQL
   CREATE DATABASE ialina_db;
   \q
   ```

### 2. Ejecución de Migraciones de Base de Datos

1. Ejecuta el archivo SQL para crear las tablas necesarias:
   ```bash
   # Desde la terminal
   psql -U postgres -d ialina_db -f db.sql
   
   # O si tienes una contraseña configurada
   PGPASSWORD=tucontraseña psql -U postgres -d ialina_db -f db.sql
   ```

### 3. Instalación de Dependencias Python

1. Es recomendable crear un entorno virtual:
   ```bash
   python -m venv venv
   
   # Activación en Linux/macOS
   source venv/bin/activate
   
   # Activación en Windows
   venv\Scripts\activate
   ```

2. Instala las dependencias del proyecto:
   ```bash
   pip install flask psycopg2-binary requests python-dotenv
   ```

### 4. Configuración del Archivo .env

1. Asegúrate de que el archivo `.env` contenga las siguientes variables:
   ```
   # API Keys
   DEEPAI_API_KEY=tu_api_key_de_deepai
   WIT_API_TOKEN=tu_token_de_wit_ai
   
   # Database configuration
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=ialina_db
   DB_USER=postgres
   DB_PASSWORD=tu_contraseña_postgres
   
   # Flask secret key
   SECRET_KEY=una_clave_secreta_larga_y_aleatoria
   ```

2. Puedes obtener claves API gratuitas en:
   - [DeepAI](https://deepai.org/) - Para reconocimiento de imágenes
   - [Wit.ai](https://wit.ai/) - Para procesamiento de lenguaje natural

### 5. Ejecución de la Aplicación

1. Una vez configurado todo, ejecuta la aplicación:
   ```bash
   python app.py
   ```

2. Accede a la aplicación en tu navegador:
   ```
   http://localhost:5001
   ```

## Uso del Sistema

### Registro de Usuario

1. Al acceder a la aplicación, serás dirigido a la página de bienvenida
2. Haz clic en la pestaña "Registrarse"
3. Completa el formulario con:
   - Nombre de usuario
   - Alias (nombre visible)
   - Contraseña (mínimo 6 caracteres)
   - Confirmación de contraseña
4. Haz clic en el botón "Registrarse"
5. Serás redirigido automáticamente al chatbot si el registro es exitoso

### Inicio de Sesión

1. En la página de bienvenida, completa el formulario de inicio de sesión
2. Ingresa tu nombre de usuario y contraseña
3. Haz clic en "Iniciar Sesión"
4. Serás redirigido al chatbot si las credenciales son correctas

### Uso del Chatbot

1. El chatbot te saludará cuando accedas
2. Puedes hacer preguntas sobre:
   - Vocales (ej. "¿Cuáles son las vocales?")
   - Alfabeto (ej. "Enséñame el abecedario")
   - Letras específicas (ej. "Letra A")
   - Palabras (ej. "Cómo se escribe casa")
3. El chatbot responderá y te guiará en el aprendizaje

### Reconocimiento de Imágenes

1. En la sección de "Reconocimiento de Objetos", haz clic en "Activar Cámara"
2. Permite el acceso a la cámara web cuando el navegador lo solicite
3. Enfoca un objeto y haz clic en "Captu
