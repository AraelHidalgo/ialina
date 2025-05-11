from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
import requests
import os
import random
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from collections import defaultdict
from dotenv import load_dotenv
from datetime import datetime, timedelta
import atexit
import signal
import hashlib
import secrets
from functools import wraps

# Importar funciones FIFO para base de datos
from database_fifo_handler import (
    guardar_usuario_fifo, guardar_mensaje_fifo, obtener_mensajes_usuario_fifo,
    start_db_worker, stop_db_worker, set_db_pool, process_remaining_tasks
)

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(16))
app.permanent_session_lifetime = timedelta(days=1)

# Contexto de conversación por usuario
CONVERSATION_CONTEXT = defaultdict(dict)

# Configuración de APIs
DEEPAI_API_KEY = os.getenv('DEEPAI_API_KEY')
WIT_API_TOKEN = os.getenv('WIT_API_TOKEN')

# Configuración de la base de datos PostgreSQL
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'ialina_db')
DB_USER = os.getenv('DB_USER', 'ialina_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', '12345')

# Base de conocimiento mejorada
RESPONSES = {
    "saludo": [
        "¡Hola! Soy tu asistente para aprender a leer y escribir. ¿En qué puedo ayudarte hoy?",
        "¡Hola! ¿Qué te gustaría aprender hoy? Podemos practicar letras o palabras."
    ],
    "despedida": [
        "¡Hasta luego! Recuerda practicar lo aprendido.",
        "¡Adiós! Siempre estoy aquí para ayudarte a aprender."
    ],
    "alfabeto": [
        "Vamos a aprender el alfabeto. Las letras son: A-B-C-D-E-F-G-H-I-J-K-L-M-N-Ñ-O-P-Q-R-S-T-U-V-W-X-Y-Z",
        "El alfabeto tiene 27 letras. ¿Quieres practicar alguna en particular?"
    ],
    "vocales": [
        "Las vocales son: A, E, I, O, U. ¿Quieres que te enseñe a escribir alguna?",
        "A-E-I-O-U. Las vocales son la base de todas las palabras."
    ],
    "letra": [
        "¡Excelente elección! La letra {} se escribe así: {}",
        "Para escribir la letra {}: {}"
    ],
    "palabra": [
        "La palabra '{}' se escribe así: {}",
        "¡Vamos a deletrear '{}': {}"
    ],
    "default": [
        "No estoy seguro de entender. ¿Podrías preguntarme sobre letras o palabras?",
        "Todavía estoy aprendiendo. ¿Quieres practicar el abecedario o alguna palabra?"
    ]
}

# Ejemplos de letras y palabras
LETTER_EXAMPLES = {
    'A': 'como en "Avión" (A-V-I-Ó-N) o "Árbol" (Á-R-B-O-L)',
    'B': 'como en "Barco" (B-A-R-C-O) o "Bota" (B-O-T-A)',
    'C': 'como en "Casa" (C-A-S-A) o "Coche" (C-O-C-H-E)',
    'M': 'como en "Manzana" (M-A-N-Z-A-N-A)',
    'P': 'como en "Perro" (P-E-R-R-O)',
    'S': 'como en "Sol" (S-O-L)'
}

# Configuración del Pool de conexiones a PostgreSQL
db_pool = None
try:
    db_pool = pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=10,
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    # Inicializar el pool en el módulo FIFO
    set_db_pool(db_pool)
    print(f"Conexión a la base de datos establecida correctamente en {DB_HOST}:{DB_PORT}/{DB_NAME}")
except Exception as e:
    db_pool = None
    print(f"Error al conectar a la base de datos: {e}")

def get_db_connection():
    """Obtiene una conexión del pool"""
    if db_pool:
        try:
            conn = db_pool.getconn()
            return conn
        except Exception as e:
            print(f"Error al obtener conexión del pool: {e}")
    return None

def release_db_connection(conn):
    """Devuelve una conexión al pool"""
    if db_pool and conn:
        db_pool.putconn(conn)

def execute_db_query(query, params=None, fetch=True):
    """Ejecuta una consulta en la base de datos con manejo de errores"""
    conn = None
    result = None
    
    try:
        conn = get_db_connection()
        if not conn:
            print("No se pudo obtener conexión a la base de datos")
            return None
            
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            
            if fetch:
                result = cursor.fetchall()
            conn.commit()
            
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error en la consulta a la base de datos: {e}")
        return None
    finally:
        if conn:
            release_db_connection(conn)
            
    return result

# Funciones para gestionar usuarios
def hash_password(password):
    """Hashea una contraseña para guardarla de forma segura"""
    return hashlib.sha256(password.encode()).hexdigest()

def verificar_usuario(username, password):
    """Verifica las credenciales de un usuario"""
    try:
        hashed_password = hash_password(password)
        query = """
        SELECT id_usuario, username, alias
        FROM usuario_app
        WHERE username = %s AND password = %s
        """
        result = execute_db_query(query, (username, hashed_password), fetch=True)
        if result and len(result) > 0:
            return result[0]
        return None
    except Exception as e:
        print(f"Error al verificar usuario: {e}")
        return None

def crear_usuario(username, password, alias=None):
    """Crea un nuevo usuario en la base de datos"""
    try:
        # Verificar si el usuario ya existe
        query_check = """
        SELECT username
        FROM usuario_app
        WHERE username = %s
        """
        result = execute_db_query(query_check, (username,), fetch=True)
        if result and len(result) > 0:
            return False, "El nombre de usuario ya está en uso"
        
        # Crear el nuevo usuario
        hashed_password = hash_password(password)
        id_usuario = f"user_{secrets.token_hex(8)}"
        
        query = """
        INSERT INTO usuario_app (id_usuario, username, password, alias)
        VALUES (%s, %s, %s, %s)
        RETURNING id_usuario
        """
        result = execute_db_query(query, (id_usuario, username, hashed_password, alias), fetch=True)
        if result and len(result) > 0:
            return True, id_usuario
        return False, "Error al crear el usuario"
    except Exception as e:
        print(f"Error al crear usuario: {e}")
        return False, str(e)

# Decorador para rutas que requieren autenticación
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('welcome'))
        return f(*args, **kwargs)
    return decorated_function

# Rutas de autenticación y página principal
@app.route('/')
def welcome():
    if 'user_id' in session:
        return redirect(url_for('chatbot'))
    return render_template('welcome.html')

@app.route('/login', methods=['POST'])
def login():
    if request.is_json:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
    else:
        username = request.form.get('username')
        password = request.form.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'Nombre de usuario y contraseña son requeridos'})
    
    user = verificar_usuario(username, password)
    if user:
        session.permanent = True
        session['user_id'] = user['id_usuario']
        session['username'] = user['username']
        session['alias'] = user['alias']
        
        return jsonify({'success': True, 'redirect': url_for('chatbot')})
    else:
        return jsonify({'success': False, 'message': 'Credenciales inválidas'})

@app.route('/register', methods=['POST'])
def register():
    if request.is_json:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        alias = data.get('alias')
    else:
        username = request.form.get('username')
        password = request.form.get('password')
        alias = request.form.get('alias')
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'Nombre de usuario y contraseña son requeridos'})
    
    success, result = crear_usuario(username, password, alias)
    if success:
        session.permanent = True
        session['user_id'] = result
        session['username'] = username
        session['alias'] = alias
        
        # Usar FIFO para guardar el usuario
        guardar_usuario_fifo(result, alias)
        
        return jsonify({'success': True, 'redirect': url_for('chatbot')})
    else:
        return jsonify({'success': False, 'message': result})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('welcome'))

@app.route('/chatbot')
@login_required
def chatbot():
    return render_template('index.html')

@app.route('/api/recognize', methods=['POST'])
def recognize_image():
    """Endpoint para reconocimiento de imágenes"""
    print("Recibiendo solicitud de reconocimiento de imagen")
    
    if 'image' not in request.files:
        print("Error: No se recibió archivo 'image'")
        return jsonify({'success': False, 'error': 'No se recibió imagen'}), 400
    
    image_file = request.files['image']
    
    if image_file.filename == '':
        print("Error: Archivo sin nombre")
        return jsonify({'success': False, 'error': 'Archivo sin nombre'}), 400
    
    if not DEEPAI_API_KEY or DEEPAI_API_KEY == 'a79f08a8-2db7-4e91-9dcd-54c463fd00f2':
        print("Error: API Key no configurada")
        return jsonify({
            'success': False,
            'error': 'API Key no configurada',
            'suggestion': 'Obtenga una API Key gratuita en https://deepai.org/'
        }), 400
    
    try:
        response = requests.post(
            "https://api.deepai.org/api/image-recognition",
            files={'image': image_file},
            headers={'api-key': DEEPAI_API_KEY},
            timeout=20
        )
        response.raise_for_status()
        result = response.json()
        print("Respuesta de DeepAI:", result)
        
        if 'output' in result and isinstance(result['output'], list):
            labels = result['output'][:3]  # Top 3 resultados
            message = f"Reconocí estos objetos: {', '.join(labels)}. ¿Quieres aprender a escribir alguna de estas palabras?"
            
            return jsonify({
                'success': True,
                'objects': labels,
                'message': message,
                'type': 'object_recognition'
            })
        
        return jsonify({'success': False, 'error': 'No se detectaron objetos claros'})
        
    except requests.exceptions.RequestException as e:
        print(f"Error en la API DeepAI: {str(e)}")
        return jsonify({
            'success': False, 
            'error': f'Error al comunicarse con el servicio de reconocimiento: {str(e)}'
        }), 500
    except Exception as e:
        print(f"Error inesperado: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ask', methods=['POST'])
def handle_educational_chat():
    """Endpoint para el chatbot educativo"""
    print("Recibiendo mensaje del chatbot")
    
    try:
        if not request.is_json:
            return jsonify({'reply': 'Formato no válido', 'status': 'error'}), 400
            
        data = request.get_json()
        user_message = data.get('message', '').strip().lower()
        
        # Usar el ID de usuario de la sesión si está disponible
        if 'user_id' in session:
            user_id = session['user_id']
        else:
            user_id = data.get('user_id', 'default')
        
        if not user_message:
            return jsonify({'reply': 'Escribe tu mensaje', 'status': 'error'}), 400
        
        print(f"Mensaje recibido: {user_message}")
        
        # Guardar el usuario en la base de datos usando FIFO
        if 'user_id' in session:
            guardar_usuario_fifo(user_id, session.get('alias'))
        
        # Intenta con Wit.ai si está configurado
        if WIT_API_TOKEN and WIT_API_TOKEN != 'JXAVSNXFEAVH3BXQ72AGWKY4O4H237I7':
            try:
                print("Intentando con Wit.ai...")
                wit_response = requests.get(
                    f'https://api.wit.ai/message?v=20240429&q={user_message}',
                    headers={'Authorization': f'Bearer {WIT_API_TOKEN}'},
                    timeout=5
                )
                wit_response.raise_for_status()
                wit_data = wit_response.json()
                print("Respuesta de Wit.ai:", wit_data)
                
                if wit_data.get('intents'):
                    intent = wit_data['intents'][0]['name']
                    entities = wit_data.get('entities', {})
                    print(f"Intención detectada: {intent}, Entidades: {entities}")
                    response = generate_response(intent, entities)
                    
                    # Guardar el mensaje del usuario en la base de datos usando FIFO
                    guardar_mensaje_fifo(user_id, "usuario", user_message)
                    
                    # Guardar la respuesta del bot en la base de datos usando FIFO
                    if 'reply' in response.json:
                        guardar_mensaje_fifo(user_id, "bot", response.json['reply'])
                    
                    # Guardar contexto
                    if 'type' in response.json:
                        CONVERSATION_CONTEXT[user_id]['last_type'] = response.json['type']
                    return response
            except requests.exceptions.RequestException as e:
                print(f"Error con Wit.ai: {str(e)}")
        
        # Respuestas básicas si Wit.ai falla
        response = generate_basic_response(user_message, user_id)
        
        # Guardar el mensaje del usuario en la base de datos usando FIFO
        guardar_mensaje_fifo(user_id, "usuario", user_message)
        
        # Guardar la respuesta del bot en la base de datos usando FIFO
        if 'reply' in response.json:
            guardar_mensaje_fifo(user_id, "bot", response.json['reply'])
        
        # Guardar contexto
        if 'type' in response.json:
            CONVERSATION_CONTEXT[user_id]['last_type'] = response.json['type']
        return response
        
    except Exception as e:
        print(f"Error general: {str(e)}")
        return jsonify({'reply': 'Ocurrió un error', 'error': str(e), 'status': 'error'}), 500

@app.route('/api/witai', methods=['POST'])
def handle_witai_chat():
    """Endpoint exclusivo para Wit.ai"""
    print("Recibiendo solicitud para Wit.ai")
    
    try:
        if not request.is_json:
            return jsonify({'reply': 'Formato no válido', 'status': 'error'}), 400
            
        data = request.get_json()
        user_message = data.get('message', '').strip().lower()
        user_id = data.get('user_id', 'default')
        
        if not user_message:
            return jsonify({'reply': 'Escribe tu mensaje', 'status': 'error'}), 400
        
        print(f"Procesando con Wit.ai: {user_message}")
        
        if not WIT_API_TOKEN or WIT_API_TOKEN == 'JXAVSNXFEAVH3BXQ72AGWKY4O4H237I7':
            return jsonify({
                'reply': 'Wit.ai no configurado',
                'status': 'error'
            }), 400
        
        wit_response = requests.get(
            f'https://api.wit.ai/message?v=20240429&q={user_message}',
            headers={'Authorization': f'Bearer {WIT_API_TOKEN}'},
            timeout=5
        )
        wit_response.raise_for_status()
        wit_data = wit_response.json()
        print("Respuesta completa de Wit.ai:", wit_data)
        
        if wit_data.get('intents'):
            intent = wit_data['intents'][0]['name']
            entities = wit_data.get('entities', {})
            print(f"Intención detectada: {intent}, Entidades: {entities}")
            response = generate_response(intent, entities)
            # Guardar contexto
            if 'type' in response.json:
                CONVERSATION_CONTEXT[user_id]['last_type'] = response.json['type']
            return response
        
        return jsonify({
            'reply': "No entendí tu solicitud. ¿Podrías reformularla?",
            'status': 'success'
        })
        
    except requests.exceptions.RequestException as e:
        print(f"Error de conexión: {str(e)}")
        return jsonify({
            'reply': 'Error al conectar con Wit.ai. Intenta más tarde.',
            'status': 'error'
        }), 503
    except Exception as e:
        print(f"Error inesperado: {str(e)}")
        return jsonify({
            'reply': 'Error inesperado al procesar tu mensaje.',
            'error': str(e),
            'status': 'error'
        }), 500

def generate_response(intent, entities):
    """Genera respuestas basadas en intenciones"""
    print(f"Generando respuesta para intención: {intent}")
    
    # Manejar saludos
    if intent == "saludo":
        return jsonify({
            'reply': random.choice(RESPONSES['saludo']),
            'status': 'success',
            'type': 'saludo'
        })
    
    # Manejar despedidas
    if intent == "despedida":
        return jsonify({
            'reply': random.choice(RESPONSES['despedida']),
            'status': 'success',
            'type': 'despedida'
        })
    
    # Manejar letras
    if intent == "learn_letter" and entities.get('letra'):
        letter = entities['letra'][0]['body'].upper()
        example = LETTER_EXAMPLES.get(letter, f"La letra {letter} aparece en muchas palabras")
        return jsonify({
            'reply': random.choice(RESPONSES['letra']).format(letter, example),
            'status': 'success',
            'type': 'letra_info',
            'letter': letter
        })
    
    # Manejar palabras
    if intent == "learn_word" and entities.get('palabra'):
        word = entities['palabra'][0]['body']
        spelling = "-".join([f"'{l.upper()}'" for l in word])
        return jsonify({
            'reply': random.choice(RESPONSES['palabra']).format(word, spelling),
            'status': 'success',
            'type': 'palabra_info',
            'word': word
        })
    
    # Respuesta por defecto
    return jsonify({
        'reply': random.choice(RESPONSES['default']),
        'status': 'success'
    })

def generate_basic_response(message, user_id='default'):
    """Genera respuestas educativas básicas con mejor manejo de contexto"""
    print(f"Generando respuesta básica para: {message}")
    
    message_lower = message.lower()
    context = CONVERSATION_CONTEXT[user_id]
    
    # Detección mejorada de intenciones
    if any(word in message_lower for word in ['hola', 'hi', 'buenos días', 'buenas tardes']):
        context.clear()
        return jsonify({
            'reply': random.choice(RESPONSES['saludo']),
            'status': 'success',
            'type': 'saludo'
        })
    
    if any(word in message_lower for word in ['adiós', 'chao', 'hasta luego', 'nos vemos']):
        context.clear()
        return jsonify({
            'reply': random.choice(RESPONSES['despedida']),
            'status': 'success',
            'type': 'despedida'
        })
    
    # Detección mejorada de solicitudes específicas
    if any(word in message_lower for word in ['vocales', 'a e i o u']):
        return jsonify({
            'reply': random.choice(RESPONSES['vocales']),
            'status': 'success',
            'type': 'vocales_info'
        })
    
    if any(word in message_lower for word in ['alfabeto', 'abecedario', 'letras']):
        return jsonify({
            'reply': random.choice(RESPONSES['alfabeto']),
            'status': 'success',
            'type': 'alfabeto_info'
        })
    
    # Detección de letras específicas
    if len(message_lower.strip()) == 1 and message_lower.isalpha():
        letter = message_lower.upper()
        example = LETTER_EXAMPLES.get(letter, f"La letra {letter} aparece en muchas palabras")
        return jsonify({
            'reply': random.choice(RESPONSES['letra']).format(letter, example),
            'status': 'success',
            'type': 'letra_info',
            'letter': letter
        })
    
    # Detección de palabras específicas
    if (len(message_lower.split()) == 1 and message_lower.isalpha() and 
        len(message_lower) > 1 and not any(w in message_lower for w in ['hola', 'adios'])):
        word = message_lower
        spelling = "-".join([f"'{l.upper()}'" for l in word])
        return jsonify({
            'reply': random.choice(RESPONSES['palabra']).format(word, spelling),
            'status': 'success',
            'type': 'palabra_info',
            'word': word
        })
    
    # Manejo de contexto para preguntas de seguimiento
    if context.get('last_type') == 'vocales_info':
        if any(w in message_lower for w in ['sí', 'si', 'claro', 'por favor']):
            return jsonify({
                'reply': "¡Perfecto! Las vocales son: A (se escribe como un triángulo), E (línea horizontal con una curva), I (línea vertical), O (círculo), U (línea curva). ¿Quieres practicar escribir alguna en particular?",
                'status': 'success',
                'type': 'vocales_detalle'
            })
        elif any(w in message_lower for w in ['a', 'e', 'i', 'o', 'u']):
            vowel = message_lower.upper()
            descriptions = {
                'A': 'La A se escribe como un triángulo con una línea horizontal en el medio',
                'E': 'La E se escribe con una línea vertical y tres líneas horizontales',
                'I': 'La I es una línea vertical con un punto arriba',
                'O': 'La O es un círculo completo',
                'U': 'La U es una curva hacia abajo y luego hacia arriba'
            }
            return jsonify({
                'reply': descriptions.get(vowel, f"La vocal {vowel} es importante. ¿Quieres practicar escribirla?"),
                'status': 'success',
                'type': 'vocal_especifica'
            })
    
    if context.get('last_type') == 'alfabeto_info':
        if any(w in message_lower for w in ['sí', 'si', 'claro', 'por favor']):
            return jsonify({
                'reply': "Vamos a practicar. ¿Qué letra te gustaría aprender primero? Puedes decirme una letra como 'A', 'B', 'M', etc.",
                'status': 'success',
                'type': 'alfabeto_practica'
            })
    
    # Respuesta por defecto mejorada
    if not context.get('last_type'):
        return jsonify({
            'reply': "¿Te gustaría aprender sobre: 1) Las vocales, 2) El alfabeto completo, o 3) Cómo se escribe una palabra específica?",
            'status': 'success'
        })
    else:
        return jsonify({
            'reply': random.choice(RESPONSES['default']),
            'status': 'success'
        })

# Iniciar el worker de base de datos a través de FIFO al iniciar la aplicación
db_worker_started = False

# Función para iniciar el worker FIFO
def init_db_fifo_worker():
    global db_worker_started
    if db_pool is None:
        print("No se puede iniciar el worker FIFO: el pool de base de datos no está disponible")
        return False
    
    try:
        # Iniciar el worker de FIFO
        db_worker_started = start_db_worker()
        if db_worker_started:
            print("Worker de base de datos FIFO iniciado correctamente")
            return True
        else:
            print("No se pudo iniciar el worker de base de datos FIFO")
            return False
    except Exception as e:
        print(f"Error al iniciar worker FIFO: {e}")
        return False

# Función de limpieza para el worker FIFO
def cleanup_db_worker():
    if db_worker_started:
        try:
            print("Procesando tareas pendientes en la cola FIFO...")
            tasks_processed = process_remaining_tasks()
            print(f"Se procesaron {tasks_processed} tareas pendientes")
            
            print("Deteniendo worker de base de datos FIFO...")
            stop_db_worker()
            print("Worker de base de datos FIFO detenido correctamente")
        except Exception as e:
            print(f"Error durante la limpieza del worker FIFO: {e}")

# Registrar la función de limpieza para cuando la aplicación se cierre
atexit.register(cleanup_db_worker)

# Manejar señales para limpieza adecuada
def signal_handler(signum, frame):
    print(f"Señal {signum} recibida. Limpiando...")
    cleanup_db_worker()
    exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Iniciar el worker FIFO después de configurar todo
if db_pool is not None:
    init_db_fifo_worker()
else:
    print("No se pudo iniciar el worker FIFO: el pool de base de datos no está disponible")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
