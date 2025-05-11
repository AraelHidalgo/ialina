/* 
   Esquema de base de datos para el Asistente Educativo
   Versión ampliada con soporte para autenticación
*/

/* 1.1 Tabla de usuarios con soporte para autenticación */
CREATE TABLE usuario_app (
    id_usuario   TEXT PRIMARY KEY,              -- identificador único
    username     TEXT UNIQUE NOT NULL,          -- nombre de usuario para login
    password     TEXT NOT NULL,                 -- contraseña hasheada
    alias        TEXT,                          -- apodo o nombre mostrado opcional
    fecha_alta   TIMESTAMPTZ DEFAULT NOW()      -- cuándo se registró
);

/* 1.2 Tabla de mensajes del chat */
CREATE TABLE mensaje_chat (
    id_mensaje   BIGSERIAL PRIMARY KEY,
    id_usuario   TEXT REFERENCES usuario_app(id_usuario) ON DELETE CASCADE,
    emisor       TEXT CHECK (emisor IN ('usuario', 'bot')), -- quién habla
    contenido    TEXT NOT NULL,                 -- cuerpo del mensaje
    fecha_envio  TIMESTAMPTZ DEFAULT NOW()      -- marca de tiempo
);

/* 1.3 Guarda (o crea) al usuario y registra su mensaje */
CREATE OR REPLACE PROCEDURE registrar_mensaje_chat(
    p_id_usuario TEXT,
    p_emisor     TEXT,
    p_contenido  TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Verifica que el usuario exista (debe haberse creado en el registro)
    IF NOT EXISTS (SELECT 1 FROM usuario_app WHERE id_usuario = p_id_usuario) THEN
        RAISE EXCEPTION 'El usuario % no existe', p_id_usuario;
    END IF;

    -- Inserta el mensaje
    INSERT INTO mensaje_chat(id_usuario, emisor, contenido)
    VALUES (p_id_usuario, p_emisor, p_contenido);
END;
$$;

-- Índices para mejorar rendimiento
CREATE INDEX IF NOT EXISTS idx_usuario_username ON usuario_app(username);
CREATE INDEX IF NOT EXISTS idx_mensaje_usuario ON mensaje_chat(id_usuario);
CREATE INDEX IF NOT EXISTS idx_mensaje_fecha ON mensaje_chat(fecha_envio);

-- Comentarios
COMMENT ON TABLE usuario_app IS 'Almacena los usuarios de la aplicación con sus credenciales';
COMMENT ON TABLE mensaje_chat IS 'Almacena los mensajes intercambiados entre usuarios y el chatbot';
COMMENT ON COLUMN usuario_app.password IS 'Contraseña hasheada usando SHA-256';

