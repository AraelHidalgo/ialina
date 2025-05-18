# Variables de Entorno para IALina en Render

Al desplegar tu aplicación en Render, debes configurar las siguientes variables de entorno en la sección 'Environment Variables' del panel de configuración:

## Variables Requeridas

* **DATABASE_URL**: URL de conexión a la base de datos PostgreSQL.
  * Valor actual: `postgresql://ialina_user:memluFpWseseh6i3zjtds1OTYLIJZJTP@dpg-d0kleubuibrs739klrrg-a.oregon-postgres.render.com/ialina_db`
  * ⚠️ **Nota**: Esta variable contiene credenciales y debería manejarse como un secreto.

* **SECRET_KEY**: Clave secreta para las sesiones de Flask.
  * Ejemplo: `tu_clave_secreta_aleatoria` (usa un valor aleatorio y seguro)
  * Si no se proporciona, la aplicación generará una clave aleatoria, pero esto causará que las sesiones se invaliden cuando se reinicie la aplicación.

## Variables Opcionales

* **DEEPAI_API_KEY**: Clave API para el servicio DeepAI de reconocimiento de imágenes.
  * Regístrate en [DeepAI](https://deepai.org/) para obtener una clave gratuita.
  * Si no se proporciona, la funcionalidad de reconocimiento de imágenes no estará disponible.

* **WIT_API_TOKEN**: Token para el servicio Wit.ai de procesamiento de lenguaje natural.
  * Regístrate en [Wit.ai](https://wit.ai/) para obtener un token.
  * Si no se proporciona, la aplicación usará un procesamiento de texto básico.

## Recomendación para el Código

Para una mejor seguridad, sería recomendable modificar `app.py` para utilizar la variable de entorno DATABASE_URL en lugar de tener la URL de conexión hardcodeada:

```python
# Reemplazar esta línea en app.py:
DATABASE_URL = "postgresql://ialina_user:memluFpWseseh6i3zjtds1OTYLIJZJTP@dpg-d0kleubuibrs739klrrg-a.oregon-postgres.render.com/ialina_db"

# Por esta otra:
DATABASE_URL = os.getenv('DATABASE_URL', "postgresql://ialina_user:memluFpWseseh6i3zjtds1OTYLIJZJTP@dpg-d0kleubuibrs739klrrg-a.oregon-postgres.render.com/ialina_db")
```

Esto permitirá cambiar la URL de la base de datos mediante variables de entorno sin tener que modificar el código.

