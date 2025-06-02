# Asistente Educativo

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
