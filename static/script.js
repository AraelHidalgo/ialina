// Elementos del DOM
const DOM = {
  chatMessages: document.getElementById('chat-messages'),
  chatForm: document.getElementById('chat-form'),
  inputMessage: document.getElementById('input-message'),
  btnVoice: document.getElementById('btn-voice'),
  btnCamera: document.getElementById('btn-camera'),
  captureBtn: document.getElementById('capture-btn'),
  toggleDetection: document.getElementById('toggle-detection'),
  video: document.getElementById('video'),
  canvas: document.getElementById('canvas'),
  objectResults: document.getElementById('object-results'),
  objectResultText: document.getElementById('object-recognition-result'),
  witaiToggle: document.getElementById('witai-toggle'),
  witaiLabel: document.getElementById('witai-label')
};

// Estado de la aplicación
const AppState = {
  recognition: null,
  model: null,
  stream: null,
  isCameraActive: false,
  isModelLoaded: false,
  isSpeaking: false,
  witaiEnabled: false,
  isDetecting: false,
  detectionInterval: null,
  userId: `user_${Math.random().toString(36).substr(2, 9)}` // ID único para cada usuario
};

// Mensajes del sistema
const Messages = {
  welcome: '¡Hola! Soy tu asistente para aprender a leer y escribir. ¿En qué puedo ayudarte hoy?',
  thinking: 'Pensando...',
  listening: 'Escuchando... habla ahora.',
  error: 'Ocurrió un error. Por favor, inténtalo de nuevo.',
  micError: 'Error al acceder al micrófono. Asegúrate de permitir los permisos.',
  cameraError: 'No se pudo acceder a la cámara. Por favor, permite el acceso.',
  modelError: 'Error al cargar el modelo de reconocimiento.',
  detectionActive: 'Detección en tiempo real activada',
  detectionInactive: 'Detección en tiempo real desactivada',
  noCamera: 'Primero activa la cámara',
  processingImage: 'Procesando imagen...'
};

// Inicialización de la aplicación
async function initApp() {
  try {
    addMessage(Messages.welcome, 'bot');
    await loadModel();
    setupVoiceRecognition();
    setupCamera();
    setupWitaiToggle();
    setupEventListeners();
    setupExercises();
  } catch (error) {
    console.error('Error al inicializar la aplicación:', error);
    addMessage(Messages.error, 'bot');
  }
}

// Configuración de eventos
function setupEventListeners() {
  DOM.chatForm.addEventListener('submit', handleChatSubmit);
  DOM.captureBtn.addEventListener('click', captureAndRecognize);
  DOM.toggleDetection.addEventListener('click', toggleRealTimeDetection);
}

// Configuración del toggle de Wit.ai
function setupWitaiToggle() {
  DOM.witaiToggle.addEventListener('change', function() {
    AppState.witaiEnabled = this.checked;
    DOM.witaiLabel.textContent = this.checked ? 'Modo Avanzado' : 'Modo Básico';
    addMessage(`Modo ${this.checked ? 'avanzado' : 'básico'} activado`, 'system');
  });
}

// Carga del modelo COCO-SSD
async function loadModel() {
  try {
    addMessage('Cargando modelo de reconocimiento...', 'bot');
    AppState.model = await cocoSsd.load();
    AppState.isModelLoaded = true;
    DOM.toggleDetection.disabled = false;
    console.log('Modelo COCO-SSD cargado correctamente');
  } catch (error) {
    console.error('Error al cargar el modelo:', error);
    addMessage(Messages.modelError, 'bot');
  }
}

// Configuración del reconocimiento de voz
function setupVoiceRecognition() {
  if (!('webkitSpeechRecognition' in window)) {
    DOM.btnVoice.disabled = true;
    DOM.btnVoice.title = 'Reconocimiento de voz no soportado';
    return;
  }

  AppState.recognition = new window.webkitSpeechRecognition();
  AppState.recognition.lang = 'es-ES';
  AppState.recognition.interimResults = false;
  AppState.recognition.maxAlternatives = 1;

  AppState.recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    DOM.inputMessage.value = transcript;
    handleChatSubmit(new Event('submit'));
  };

  AppState.recognition.onerror = (event) => {
    console.error('Error en reconocimiento de voz:', event.error);
    addMessage(Messages.error, 'bot');
  };

  AppState.recognition.onend = () => {
    DOM.btnVoice.classList.remove('bg-blue-700', 'text-white');
  };

  DOM.btnVoice.addEventListener('click', toggleVoiceRecognition);
}

function toggleVoiceRecognition() {
  if (AppState.recognition && AppState.recognition.recognizing) {
    AppState.recognition.stop();
    DOM.btnVoice.classList.remove('bg-blue-700', 'text-white');
  } else {
    try {
      AppState.recognition.start();
      DOM.btnVoice.classList.add('bg-blue-700', 'text-white');
      addMessage(Messages.listening, 'bot');
      AppState.recognition.recognizing = true;
    } catch (error) {
      console.error('Error al iniciar reconocimiento:', error);
      addMessage(Messages.micError, 'bot');
    }
  }
}

// Configuración de la cámara
function setupCamera() {
  DOM.btnCamera.addEventListener('click', toggleCamera);
}

async function toggleCamera() {
  if (AppState.isCameraActive) {
    stopCamera();
    DOM.btnCamera.innerHTML = '<i class="fas fa-camera mr-2"></i> Activar Cámara';
    DOM.captureBtn.disabled = true;
    DOM.toggleDetection.disabled = true;
    DOM.objectResults.classList.add('hidden');
  } else {
    try {
      addMessage('Activando cámara...', 'bot');
      AppState.stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' },
        audio: false
      });
      
      DOM.video.srcObject = AppState.stream;
      DOM.video.onloadedmetadata = () => {
        DOM.video.play();
        AppState.isCameraActive = true;
        DOM.btnCamera.innerHTML = '<i class="fas fa-stop mr-2"></i> Desactivar';
        DOM.captureBtn.disabled = false;
        DOM.toggleDetection.disabled = false;
      };
    } catch (error) {
      console.error('Error en cámara:', error);
      addMessage(Messages.cameraError, 'bot');
    }
  }
}

function stopCamera() {
  if (AppState.stream) {
    AppState.stream.getTracks().forEach(track => track.stop());
    AppState.stream = null;
  }
  DOM.video.srcObject = null;
  AppState.isCameraActive = false;
  stopRealTimeDetection();
}

// Detección en tiempo real
function toggleRealTimeDetection() {
  if (!AppState.isCameraActive) {
    addMessage(Messages.noCamera, 'bot');
    return;
  }

  AppState.isDetecting = !AppState.isDetecting;
  
  if (AppState.isDetecting) {
    DOM.toggleDetection.innerHTML = '<i class="fas fa-eye-slash mr-2"></i> Detener';
    addMessage(Messages.detectionActive, 'system');
    startRealTimeDetection();
  } else {
    DOM.toggleDetection.innerHTML = '<i class="fas fa-eye mr-2"></i> Detección en Vivo';
    addMessage(Messages.detectionInactive, 'system');
    stopRealTimeDetection();
  }
}

function startRealTimeDetection() {
  const video = DOM.video;
  const canvas = DOM.canvas;
  const ctx = canvas.getContext('2d');
  
  clearDetections();
  
  AppState.detectionInterval = setInterval(async () => {
    if (!AppState.isDetecting) return;
    
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    try {
      const predictions = await AppState.model.detect(canvas);
      displayDetections(predictions);
    } catch (error) {
      console.error('Error en detección:', error);
    }
  }, 1000);
}

function stopRealTimeDetection() {
  clearInterval(AppState.detectionInterval);
  clearDetections();
}

function displayDetections(predictions) {
  const video = DOM.video;
  clearDetections();
  
  predictions.forEach(prediction => {
    if (prediction.score < 0.5) return;
    
    const box = document.createElement('div');
    box.className = 'detection-box';
    box.style.left = `${prediction.bbox[0]}px`;
    box.style.top = `${prediction.bbox[1]}px`;
    box.style.width = `${prediction.bbox[2]}px`;
    box.style.height = `${prediction.bbox[3]}px`;
    video.parentNode.appendChild(box);
    
    const label = document.createElement('div');
    label.className = 'object-label';
    label.textContent = `${prediction.class} (${Math.round(prediction.score * 100)}%)`;
    label.style.left = `${prediction.bbox[0]}px`;
    label.style.top = `${prediction.bbox[1] - 20}px`;
    video.parentNode.appendChild(label);
  });
}

function clearDetections() {
  document.querySelectorAll('.detection-box, .object-label').forEach(el => el.remove());
}

// Capturar y reconocer imagen
async function captureAndRecognize() {
  if (!AppState.isCameraActive || !AppState.stream) {
    addMessage(Messages.noCamera, 'bot');
    return;
  }

  const canvas = DOM.canvas;
  const video = DOM.video;
  const context = canvas.getContext('2d');
  
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  context.drawImage(video, 0, 0, canvas.width, canvas.height);
  
  try {
    const blob = await new Promise((resolve) => {
      canvas.toBlob(resolve, 'image/jpeg', 0.8);
    });
    
    if (!blob) {
      throw new Error("No se pudo capturar la imagen");
    }

    const formData = new FormData();
    formData.append('image', blob, 'capture.jpg');
    
    const processingMsg = addMessage(Messages.processingImage, 'bot');
    
    const response = await fetch('/api/recognize', {
      method: 'POST',
      body: formData
    });
    
    if (!response.ok) {
      throw new Error(`Error: ${response.status}`);
    }

    const data = await response.json();
    
    // Eliminar el mensaje de procesamiento
    if (processingMsg && processingMsg.parentNode === DOM.chatMessages) {
      DOM.chatMessages.removeChild(processingMsg);
    }
    
    if (data.success) {
      addMessage(data.message, 'bot', canvas.toDataURL('image/jpeg'));
      DOM.objectResults.classList.remove('hidden');
      DOM.objectResultText.textContent = `Objetos detectados: ${data.objects.join(', ')}`;
      
      // Preguntar si quiere aprender sobre el primer objeto detectado
      setTimeout(() => {
        addMessage(`¿Quieres aprender a escribir "${data.objects[0]}"?`, 'bot');
      }, 1000);
    } else {
      addMessage(data.error || "Error al reconocer la imagen", 'bot');
    }
  } catch (error) {
    console.error('Error en reconocimiento:', error);
    addMessage(`Error: ${error.message}`, 'bot');
  }
}

// Manejo del chat mejorado
async function handleChatSubmit(e) {
  if (e) e.preventDefault();
  const message = DOM.inputMessage.value.trim();
  if (!message) return;

  const userMessage = addMessage(message, 'user');
  DOM.inputMessage.value = '';
  
  const thinkingMsg = addMessage(Messages.thinking, 'bot');
  
  try {
    const endpoint = AppState.witaiEnabled ? '/api/witai' : '/api/ask';
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        message: message,
        user_id: AppState.userId  // Enviar ID de usuario único
      })
    });

    if (!response.ok) throw new Error(`Error HTTP: ${response.status}`);
    
    const data = await response.json();
    
    // Reemplazar el mensaje "Pensando..." con la respuesta real
    if (thinkingMsg && thinkingMsg.parentNode === DOM.chatMessages) {
      DOM.chatMessages.removeChild(thinkingMsg);
    }
    
    if (data.reply) {
      addMessage(data.reply, 'bot');
      speak(data.reply);
      
      // Manejar acciones especiales basadas en el tipo de respuesta
      if (data.type === 'vocales_info') {
        // Podemos agregar botones rápidos para las vocales
        setTimeout(() => {
          const quickReplies = document.createElement('div');
          quickReplies.className = 'flex space-x-2 mt-2';
          
          ['A', 'E', 'I', 'O', 'U'].forEach(vowel => {
            const btn = document.createElement('button');
            btn.className = 'bg-blue-100 text-blue-800 px-3 py-1 rounded-md hover:bg-blue-200';
            btn.textContent = vowel;
            btn.onclick = () => {
              DOM.inputMessage.value = vowel;
              handleChatSubmit(new Event('submit'));
            };
            quickReplies.appendChild(btn);
          });
          
          DOM.chatMessages.querySelector('.bot-message:last-child').appendChild(quickReplies);
        }, 300);
      }
    } else {
      addMessage("No recibí una respuesta válida", 'bot');
    }
  } catch (error) {
    if (thinkingMsg && thinkingMsg.parentNode === DOM.chatMessages) {
      DOM.chatMessages.removeChild(thinkingMsg);
    }
    console.error('Error en el chat:', error);
    addMessage(`Error: ${error.message}`, 'bot');
  }
}

// Text-to-Speech mejorado
function speak(text) {
  if (!('speechSynthesis' in window)) {
    console.warn('Text-to-Speech no soportado en este navegador');
    return;
  }
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'es-ES';
  utterance.rate = 0.8;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

// Función para agregar mensajes al chat con mejor formato
function addMessage(text, sender = 'bot', imageUrl = null) {
  const messageElement = document.createElement('div');
  messageElement.className = `flex ${sender === 'user' ? 'justify-end' : 'justify-start'} mb-3`;
  
  const messageContent = document.createElement('div');
  messageContent.className = sender === 'user' 
    ? 'user-message bg-blue-600 text-white rounded-lg px-4 py-2 max-w-xs lg:max-w-md break-words'
    : 'bot-message bg-gray-200 text-gray-900 rounded-lg px-4 py-2 max-w-xs lg:max-w-md break-words';
  
  messageContent.textContent = text;
  messageElement.appendChild(messageContent);
  
  if (imageUrl) {
    const imgElement = document.createElement('img');
    imgElement.src = imageUrl;
    imgElement.alt = 'Imagen capturada';
    imgElement.className = 'w-full h-auto rounded-lg mt-2 max-w-xs';
    imgElement.loading = 'lazy';
    messageContent.appendChild(imgElement);
  }
  
  DOM.chatMessages.appendChild(messageElement);
  DOM.chatMessages.scrollTop = DOM.chatMessages.scrollHeight;
  
  return messageElement;
}

// Configuración de ejercicios interactivos (se mantiene igual)
function setupExercises() {
  setupLetterIdentification();
  setupSpellingExercise();
  setupDragAndDropExercise();
}

function setupLetterIdentification() {
  document.querySelectorAll('.exercise-btn').forEach(btn => {
    btn.addEventListener('click', function() {
      const isCorrect = this.dataset.correct === 'true';
      const feedback = document.getElementById('exercise1-feedback');
      
      if (isCorrect) {
        this.classList.add('bg-green-100', 'border-green-500');
        feedback.textContent = '¡Correcto! "Manzana" empieza con M.';
        feedback.className = 'mt-3 text-center font-semibold text-green-600';
        speak('¡Correcto! Manzana empieza con la letra M.');
      } else {
        this.classList.add('bg-red-100', 'border-red-500', 'shake');
        feedback.textContent = 'Intenta nuevamente. Busca una palabra que empiece con M.';
        feedback.className = 'mt-3 text-center font-semibold text-red-600';
        speak('No es correcto. Intenta de nuevo.');
        
        setTimeout(() => {
          this.classList.remove('shake');
        }, 500);
      }
    });
  });
}

function setupSpellingExercise() {
  const inputs = document.querySelectorAll('.exercise-input');
  const checkButton = document.getElementById('check-spelling');
  const feedback = document.getElementById('exercise2-feedback');
  
  inputs.forEach((input, index) => {
    input.addEventListener('input', (e) => {
      if (e.target.value.length === 1 && index < inputs.length - 1) {
        inputs[index + 1].focus();
      }
    });
    
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Backspace' && e.target.value.length === 0 && index > 0) {
        inputs[index - 1].focus();
      }
    });
  });
  
  checkButton.addEventListener('click', () => {
    const spelling = Array.from(inputs).map(input => input.value.toUpperCase()).join('');
    
    if (spelling === 'SOL') {
      inputs.forEach(input => {
        input.classList.add('bg-green-100', 'border-green-500');
      });
      feedback.textContent = '¡Excelente! S-O-L es "Sol".';
      feedback.className = 'mt-3 text-center font-semibold text-green-600';
      speak('¡Excelente! Sol se deletrea S-O-L.');
    } else {
      inputs.forEach(input => {
        input.classList.add('bg-red-100', 'border-red-500');
      });
      feedback.textContent = 'La palabra "Sol" se escribe S-O-L. Intenta nuevamente.';
      feedback.className = 'mt-3 text-center font-semibold text-red-600';
      speak('No es correcto. Sol se deletrea S-O-L.');
    }
  });
}

function setupDragAndDropExercise() {
  let draggedItem = null;

  document.querySelectorAll('.draggable-letter').forEach(letter => {
    letter.addEventListener('dragstart', function() {
      draggedItem = this;
      this.classList.add('opacity-50');
    });

    letter.addEventListener('dragend', function() {
      this.classList.remove('opacity-50');
    });
  });

  document.querySelectorAll('.dropzone').forEach(zone => {
    zone.addEventListener('dragover', e => {
      e.preventDefault();
      zone.classList.add('border-blue-700', 'bg-blue-50');
    });
    
    zone.addEventListener('dragleave', () => {
      zone.classList.remove('border-blue-700', 'bg-blue-50');
    });
    
    zone.addEventListener('drop', e => {
      e.preventDefault();
      zone.classList.remove('border-blue-700', 'bg-blue-50');
      
      if (draggedItem) {
        zone.innerHTML = '';
        const clonedItem = draggedItem.cloneNode(true);
        clonedItem.classList.remove('opacity-50');
        clonedItem.draggable = false;
        zone.appendChild(clonedItem);
      }
    });
  });

  document.getElementById('check-match').addEventListener('click', () => {
    const allCorrect = Array.from(document.querySelectorAll('.dropzone')).every(zone => {
      const letter = zone.querySelector('.draggable-letter');
      return letter && letter.textContent.trim() === zone.dataset.letter;
    });

    const feedback = document.getElementById('exercise3-feedback');
    
    if (allCorrect) {
      feedback.textContent = '¡Perfecto! Has emparejado todas las letras correctamente.';
      feedback.className = 'mt-3 text-center font-semibold text-green-600';
      speak('¡Perfecto! Todas las letras están emparejadas correctamente.');
    } else {
      feedback.textContent = 'Algunas letras no están emparejadas correctamente. Intenta nuevamente.';
      feedback.className = 'mt-3 text-center font-semibold text-red-600';
      speak('Algunas letras no están correctas. Intenta nuevamente.');
    }
  });
}

// Inicializar la aplicación cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', initApp);

// Asegurar que las voces estén cargadas para TTS
window.speechSynthesis.onvoiceschanged = function() {
  console.log('Voces cargadas:', window.speechSynthesis.getVoices());
};