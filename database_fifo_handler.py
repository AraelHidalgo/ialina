"""
Database FIFO Handler Module

This module implements a thread-based FIFO queue for database operations, 
allowing asynchronous processing of database queries while maintaining
thread safety and ensuring proper connection pool usage.

It works in conjunction with the app.py database connection pool.
"""

import queue
import threading
import time
import logging
import traceback
from datetime import datetime
from psycopg2.extras import RealDictCursor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('database_fifo')

# Global variables
db_queue = queue.Queue()
worker_thread = None
should_stop = threading.Event()

# Import DB pool from app - we'll use it to get connections
# Note: This will be initialized when app.py imports this module
db_pool = None

def set_db_pool(pool):
    """
    Set the database connection pool from app.py
    
    This function should be called from app.py after creating the database pool
    to share the connection pool with this module.
    
    Args:
        pool: The psycopg2 connection pool object
    """
    global db_pool
    db_pool = pool
    logger.info("Database pool assigned to FIFO handler")

def get_db_connection():
    """Gets a connection from the pool"""
    if not db_pool:
        logger.error("Database pool not initialized")
        return None
    
    try:
        conn = db_pool.getconn()
        return conn
    except Exception as e:
        logger.error(f"Error getting connection from pool: {e}")
        return None

def release_db_connection(conn):
    """Returns a connection to the pool"""
    if not db_pool or not conn:
        return
    
    try:
        db_pool.putconn(conn)
    except Exception as e:
        logger.error(f"Error returning connection to pool: {e}")

# Task types for the queue
class TaskType:
    SAVE_USER = 'save_user'
    SAVE_MESSAGE = 'save_message'
    GET_MESSAGES = 'get_messages'

class DatabaseTask:
    """Class to represent a database task in the queue"""
    def __init__(self, task_type, params, callback=None):
        self.task_type = task_type
        self.params = params
        self.callback = callback
        self.result = None
        self.error = None
        self.completed = threading.Event()
    
    def mark_completed(self, result=None, error=None):
        """Mark task as completed"""
        self.result = result
        self.error = error
        self.completed.set()
        
        # Execute callback if provided
        if self.callback:
            try:
                self.callback(self.result, self.error)
            except Exception as e:
                logger.error(f"Error in callback: {e}")

def worker_function():
    """Worker thread function to process database tasks"""
    logger.info("Database worker thread started")
    
    while not should_stop.is_set() or not db_queue.empty():
        try:
            # Get task with timeout to allow checking should_stop periodically
            try:
                task = db_queue.get(timeout=1.0)
            except queue.Empty:
                continue
            
            # Process the task
            conn = None
            try:
                conn = get_db_connection()
                if not conn:
                    logger.error(f"Failed to get database connection for task {task.task_type}")
                    task.mark_completed(error="Database connection error")
                    continue
                
                # Process based on task type
                if task.task_type == TaskType.SAVE_USER:
                    result = process_save_user(conn, task.params)
                    task.mark_completed(result=result)
                
                elif task.task_type == TaskType.SAVE_MESSAGE:
                    result = process_save_message(conn, task.params)
                    task.mark_completed(result=result)
                
                elif task.task_type == TaskType.GET_MESSAGES:
                    result = process_get_messages(conn, task.params)
                    task.mark_completed(result=result)
                
                else:
                    logger.warning(f"Unknown task type: {task.task_type}")
                    task.mark_completed(error=f"Unknown task type: {task.task_type}")
            
            except Exception as e:
                logger.error(f"Error processing task {task.task_type}: {e}")
                logger.error(traceback.format_exc())
                task.mark_completed(error=str(e))
            
            finally:
                if conn:
                    release_db_connection(conn)
                db_queue.task_done()
        
        except Exception as e:
            logger.error(f"Unhandled error in worker thread: {e}")
            logger.error(traceback.format_exc())
            time.sleep(1)  # Avoid tight loop on error
    
    logger.info("Database worker thread stopped")

def process_save_user(conn, params):
    """Process a save user task"""
    id_usuario = params.get('id_usuario')
    alias = params.get('alias')
    
    try:
        with conn.cursor() as cursor:
            query = """
            INSERT INTO usuario_app (id_usuario, alias)
            VALUES (%s, %s)
            ON CONFLICT (id_usuario) DO NOTHING
            RETURNING id_usuario
            """
            cursor.execute(query, (id_usuario, alias))
            result = cursor.fetchone() is not None
            conn.commit()
            logger.info(f"User saved: {id_usuario}")
            return result
    except Exception as e:
        conn.rollback()
        logger.error(f"Error saving user {id_usuario}: {e}")
        return False

def process_save_message(conn, params):
    """Process a save message task"""
    id_usuario = params.get('id_usuario')
    emisor = params.get('emisor')
    contenido = params.get('contenido')
    
    try:
        with conn.cursor() as cursor:
            query = """
            INSERT INTO mensaje_chat (id_usuario, emisor, contenido)
            VALUES (%s, %s, %s)
            """
            cursor.execute(query, (id_usuario, emisor, contenido))
            conn.commit()
            logger.info(f"Message saved for user {id_usuario} from {emisor}")
            return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Error saving message for user {id_usuario}: {e}")
        return False

def process_get_messages(conn, params):
    """Process a get messages task"""
    id_usuario = params.get('id_usuario')
    limite = params.get('limite', 10)
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            query = """
            SELECT id_mensaje, emisor, contenido, fecha_envio
            FROM mensaje_chat
            WHERE id_usuario = %s
            ORDER BY fecha_envio DESC
            LIMIT %s
            """
            cursor.execute(query, (id_usuario, limite))
            result = cursor.fetchall()
            logger.info(f"Retrieved {len(result)} messages for user {id_usuario}")
            return result if result else []
    except Exception as e:
        logger.error(f"Error getting messages for user {id_usuario}: {e}")
        return []

# Public API functions

def guardar_usuario_fifo(id_usuario, alias=None, callback=None):
    """
    Save a user to the database using FIFO queue
    
    Args:
        id_usuario: User ID
        alias: Optional user alias
        callback: Optional callback function(result, error)
    
    Returns:
        True if the task was queued successfully
    """
    try:
        task = DatabaseTask(
            TaskType.SAVE_USER,
            {'id_usuario': id_usuario, 'alias': alias},
            callback
        )
        db_queue.put(task)
        logger.debug(f"User save task queued: {id_usuario}")
        return True
    except Exception as e:
        logger.error(f"Error queueing user save task: {e}")
        return False

def guardar_mensaje_fifo(id_usuario, emisor, contenido, callback=None):
    """
    Save a message to the database using FIFO queue
    
    Args:
        id_usuario: User ID
        emisor: Message sender (usuario/bot)
        contenido: Message content
        callback: Optional callback function(result, error)
    
    Returns:
        True if the task was queued successfully
    """
    try:
        task = DatabaseTask(
            TaskType.SAVE_MESSAGE,
            {'id_usuario': id_usuario, 'emisor': emisor, 'contenido': contenido},
            callback
        )
        db_queue.put(task)
        logger.debug(f"Message save task queued for user {id_usuario}")
        return True
    except Exception as e:
        logger.error(f"Error queueing message save task: {e}")
        return False

def obtener_mensajes_usuario_fifo(id_usuario, limite=10, callback=None):
    """
    Get messages for a user from the database using FIFO queue
    
    Args:
        id_usuario: User ID
        limite: Maximum number of messages to retrieve
        callback: Optional callback function(result, error)
    
    Returns:
        Task object that can be used to wait for the result
    """
    try:
        task = DatabaseTask(
            TaskType.GET_MESSAGES,
            {'id_usuario': id_usuario, 'limite': limite},
            callback
        )
        db_queue.put(task)
        logger.debug(f"Message retrieve task queued for user {id_usuario}")
        return task
    except Exception as e:
        logger.error(f"Error queueing message retrieve task: {e}")
        if callback:
            callback(None, str(e))
        return None

def start_db_worker():
    """
    Start the database worker thread
    
    Returns:
        True if worker was started successfully
    """
    global worker_thread, should_stop
    
    try:
        if worker_thread and worker_thread.is_alive():
            logger.warning("Worker thread already running")
            return True
        
        should_stop.clear()
        worker_thread = threading.Thread(target=worker_function, daemon=True)
        worker_thread.start()
        logger.info("Database worker thread started")
        return True
    except Exception as e:
        logger.error(f"Error starting worker thread: {e}")
        return False

def stop_db_worker():
    """
    Stop the database worker thread
    
    Returns:
        True if worker was stopped successfully
    """
    global worker_thread, should_stop
    
    try:
        if not worker_thread or not worker_thread.is_alive():
            logger.warning("Worker thread not running")
            return True
        
        logger.info("Stopping database worker thread...")
        should_stop.set()
        
        # Wait for the thread to finish with timeout
        worker_thread.join(timeout=5.0)
        
        if worker_thread.is_alive():
            logger.warning("Worker thread did not stop in time")
            return False
        
        logger.info("Database worker thread stopped")
        return True
    except Exception as e:
        logger.error(f"Error stopping worker thread: {e}")
        return False

def process_remaining_tasks():
    """
    Process any remaining tasks in the queue synchronously
    
    Returns:
        Number of tasks processed
    """
    count = 0
    logger.info("Processing remaining tasks...")
    
    try:
        while not db_queue.empty():
            task = db_queue.get_nowait()
            conn = None
            
            try:
                conn = get_db_connection()
                if not conn:
                    task.mark_completed(error="Database connection error")
                    continue
                
                # Process based on task type
                if task.task_type == TaskType.SAVE_USER:
                    result = process_save_user(conn, task.params)
                    task.mark_completed(result=result)
                
                elif task.task_type == TaskType.SAVE_MESSAGE:
                    result = process_save_message(conn, task.params)
                    task.mark_completed(result=result)
                
                elif task.task_type == TaskType.GET_MESSAGES:
                    result = process_get_messages(conn, task.params)
                    task.mark_completed(result=result)
                
                count += 1
            
            except Exception as e:
                logger.error(f"Error processing remaining task: {e}")
                task.mark_completed(error=str(e))
            
            finally:
                if conn:
                    release_db_connection(conn)
                db_queue.task_done()
        
        logger.info(f"Processed {count} remaining tasks")
        return count
    
    except Exception as e:
        logger.error(f"Error in process_remaining_tasks: {e}")
        return count

