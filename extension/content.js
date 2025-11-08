// Samwaad Meet Listener - Content Script
// Captures Google Meet audio and streams to backend for transcription

(function() {
  'use strict';
  
  // Prevent double injection
  if (window.__samwaadInjected) {
    console.log('[Samwaad] Already injected, skipping');
    return;
  }
  window.__samwaadInjected = true;

  const BACKEND_BASE = 'http://localhost:8000';
  const WS_BASE = 'ws://localhost:8000/ws/call/';

  // State
  let state = {
    isMonitoring: false,
    callId: null,
    mediaStream: null,
    audioContext: null,
    processor: null,
    sourceNode: null,
    ws: null,
    audioChunks: []
  };

  // Create UI Panel
  function createPanel() {
    const panel = document.createElement('div');
    panel.id = 'samwaad-panel';
    panel.innerHTML = `
      <div class="samwaad-header">
        <span>🎙️ Samwaad Meet Listener</span>
      </div>
      <div class="samwaad-body">
        <div id="samwaad-status" class="samwaad-status">Ready</div>
        <div class="samwaad-buttons">
          <button id="samwaad-start-btn" class="samwaad-btn samwaad-btn-primary">
            Start Monitoring
          </button>
          <button id="samwaad-stop-btn" class="samwaad-btn samwaad-btn-secondary" disabled>
            Stop
          </button>
        </div>
        <div id="samwaad-log" class="samwaad-log"></div>
      </div>
    `;
    document.body.appendChild(panel);
    
    // Show panel with animation
    setTimeout(() => panel.classList.add('samwaad-visible'), 300);
    
    return panel;
  }

  // Logger
  function log(message, type = 'info') {
    console.log(`[Samwaad] ${message}`);
    
    const logDiv = document.getElementById('samwaad-log');
    if (!logDiv) return;
    
    const entry = document.createElement('div');
    entry.className = `samwaad-log-entry samwaad-log-${type}`;
    entry.textContent = message;
    logDiv.insertBefore(entry, logDiv.firstChild);
    
    // Keep only last 8 entries
    while (logDiv.children.length > 8) {
      logDiv.removeChild(logDiv.lastChild);
    }
  }

  function setStatus(message) {
    const statusDiv = document.getElementById('samwaad-status');
    if (statusDiv) {
      statusDiv.textContent = message;
    }
  }

  // Backend API calls
  async function checkBackendHealth() {
    try {
      const response = await fetch(`${BACKEND_BASE}/health`, {
        method: 'GET',
        mode: 'cors'
      });
      return response.ok;
    } catch (error) {
      return false;
    }
  }

  async function createCall(title) {
    const response = await fetch(`${BACKEND_BASE}/api/calls/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({
        platform: 'google_meet',
        contact_name: title || 'Google Meet',
        contact_email: ''
      }),
      mode: 'cors'
    });

    if (!response.ok) {
      throw new Error(`Failed to create call: ${response.status}`);
    }

    return await response.json();
  }

  // WebSocket management
  function connectWebSocket(callId) {
    return new Promise((resolve, reject) => {
      const ws = new WebSocket(`${WS_BASE}${callId}`);
      const timeout = setTimeout(() => reject(new Error('WebSocket timeout')), 10000);

      ws.onopen = () => {
        clearTimeout(timeout);
        log('✅ WebSocket connected', 'success');
        resolve(ws);
      };

      ws.onerror = (error) => {
        clearTimeout(timeout);
        reject(new Error('WebSocket connection failed'));
      };

      ws.onclose = () => {
        log('WebSocket closed', 'info');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleWebSocketMessage(data);
        } catch (error) {
          console.error('[Samwaad] WS message parse error:', error);
        }
      };
    });
  }

  function handleWebSocketMessage(data) {
    const { type, message, summary, transcript } = data;

    switch (type) {
      case 'connected':
        log('Backend ready', 'success');
        break;
      
      case 'processing_started':
        log('Processing...', 'info');
        break;
      
      case 'task_executed':
        log(`🤖 ${summary || message || 'AI action completed'}`, 'success');
        showNotification('AI Action', summary || message);
        break;
      
      case 'call_completed':
        log('✅ Transcription complete!', 'success');
        showNotification('Complete', 'Transcript ready in dashboard');
        if (transcript && transcript.text) {
          const preview = transcript.text.substring(0, 100);
          log(`📝 "${preview}${transcript.text.length > 100 ? '...' : ''}"`, 'info');
        }
        break;
      
      case 'error':
        log(`❌ ${message || 'Backend error'}`, 'error');
        break;
    }
  }

  function sendAudioConfig(ws, sampleRate) {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
    const config = {
      type: 'audio_config',
      sampleRate: sampleRate,
      channels: 1,
      sampleWidth: 2,
      isFloat32: false,
      timezone: timezone
    };

    // Send twice (backend expects this)
    ws.send(JSON.stringify(config));
    ws.send(JSON.stringify(config));
    log(`🎛️ Config: ${sampleRate}Hz, ${timezone}`, 'info');
  }

  // Audio processing
  function floatTo16BitPCM(float32Array) {
    const len = float32Array.length;
    const buffer = new ArrayBuffer(len * 2);
    const view = new DataView(buffer);
    
    for (let i = 0, offset = 0; i < len; i++, offset += 2) {
      const sample = Math.max(-1, Math.min(1, float32Array[i]));
      view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
    }
    
    return new Int16Array(buffer);
  }

  // Main monitoring functions
  async function startMonitoring() {
    const startBtn = document.getElementById('samwaad-start-btn');
    const stopBtn = document.getElementById('samwaad-stop-btn');

    try {
      startBtn.disabled = true;
      setStatus('🔍 Checking backend...');
      
      // 1. Check backend
      const isHealthy = await checkBackendHealth();
      if (!isHealthy) {
        throw new Error('Backend not running. Start it: python run.py');
      }
      log('✅ Backend is healthy', 'success');

      // 2. Request screen/tab share with audio
      setStatus('📺 Requesting screen share...');
      log('💡 Select "Tab", choose this Meet tab, and CHECK "Share audio"', 'info');

      state.mediaStream = await navigator.mediaDevices.getDisplayMedia({
        video: { displaySurface: 'browser' },
        audio: {
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false
        },
        preferCurrentTab: true
      });

      // Verify audio track exists
      const audioTracks = state.mediaStream.getAudioTracks();
      if (audioTracks.length === 0) {
        state.mediaStream.getTracks().forEach(t => t.stop());
        throw new Error('No audio captured! You must check "Share audio" checkbox');
      }

      log('✅ Tab + audio captured', 'success');

      // 3. Create call in backend
      setStatus('📞 Creating call...');
      const meetingTitle = document.title || 'Google Meet Call';
      const callData = await createCall(meetingTitle);
      state.callId = callData.id;
      log(`📞 Call ID: ${state.callId}`, 'success');

      // 4. Connect WebSocket
      setStatus('🔗 Connecting WebSocket...');
      state.ws = await connectWebSocket(state.callId);

      // 5. Setup audio processing
      setStatus('🎤 Setting up audio...');
      state.audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 48000 });
      const sampleRate = state.audioContext.sampleRate;

      state.sourceNode = state.audioContext.createMediaStreamSource(state.mediaStream);
      state.processor = state.audioContext.createScriptProcessor(4096, 1, 1);

      // Send config and start
      sendAudioConfig(state.ws, sampleRate);
      state.ws.send(JSON.stringify({ type: 'start_recording' }));

      let chunkCount = 0;

      // Process and stream audio
      state.processor.onaudioprocess = (event) => {
        if (!state.ws || state.ws.readyState !== WebSocket.OPEN) return;

        const inputData = event.inputBuffer.getChannelData(0);
        const pcmData = floatTo16BitPCM(inputData);

        try {
          state.ws.send(pcmData.buffer);
          state.audioChunks.push(pcmData.buffer);
          chunkCount++;

          if (chunkCount % 100 === 0) {
            log(`📊 ${chunkCount} chunks streamed`, 'info');
          }
        } catch (error) {
          console.error('[Samwaad] Audio send error:', error);
        }
      };

      state.sourceNode.connect(state.processor);
      state.processor.connect(state.audioContext.destination);

      // Update UI
      state.isMonitoring = true;
      startBtn.disabled = false;
      stopBtn.disabled = false;
      setStatus('🔴 LIVE - Monitoring audio');
      log('🎤 Recording both sides of audio!', 'success');

      // Handle stream stop (user stops sharing)
      state.mediaStream.getTracks()[0].addEventListener('ended', () => {
        log('⚠️ Screen share ended', 'warning');
        stopMonitoring();
      });

    } catch (error) {
      console.error('[Samwaad] Start error:', error);
      log(`❌ ${error.message}`, 'error');
      setStatus('❌ Error');
      
      startBtn.disabled = false;
      stopBtn.disabled = true;
      
      // Cleanup
      cleanup();
    }
  }

  async function stopMonitoring() {
    if (!state.isMonitoring) return;

    const startBtn = document.getElementById('samwaad-start-btn');
    const stopBtn = document.getElementById('samwaad-stop-btn');

    try {
      setStatus('⏹️ Stopping...');
      log('Stopping monitoring...', 'info');

      // Send stop message
      if (state.ws && state.ws.readyState === WebSocket.OPEN) {
        state.ws.send(JSON.stringify({ type: 'stop_recording' }));
      }

      log(`📊 Total: ${state.audioChunks.length} chunks captured`, 'info');

      // Cleanup
      cleanup();

      // Update UI
      state.isMonitoring = false;
      startBtn.disabled = false;
      stopBtn.disabled = true;
      setStatus('⏸️ Stopped');
      log('✅ Processing complete', 'success');

      // Hide panel after delay
      setTimeout(() => {
        const panel = document.getElementById('samwaad-panel');
        if (panel) {
          panel.classList.remove('samwaad-visible');
          panel.classList.add('samwaad-hidden');
        }
      }, 3000);

    } catch (error) {
      console.error('[Samwaad] Stop error:', error);
      setStatus('Error stopping');
    }
  }

  function cleanup() {
    // Stop audio processing
    if (state.processor) {
      try {
        state.processor.disconnect();
        state.processor.onaudioprocess = null;
      } catch (e) {}
      state.processor = null;
    }

    if (state.sourceNode) {
      try { state.sourceNode.disconnect(); } catch (e) {}
      state.sourceNode = null;
    }

    if (state.audioContext) {
      try { state.audioContext.close(); } catch (e) {}
      state.audioContext = null;
    }

    // Stop media stream
    if (state.mediaStream) {
      state.mediaStream.getTracks().forEach(track => track.stop());
      state.mediaStream = null;
    }

    // Close WebSocket
    if (state.ws) {
      setTimeout(() => {
        try { state.ws.close(); } catch (e) {}
        state.ws = null;
      }, 1500);
    }

    state.audioChunks = [];
  }

  function showNotification(title, message) {
    if (Notification.permission === 'granted') {
      new Notification(`Samwaad: ${title}`, { body: message });
    } else if (Notification.permission !== 'denied') {
      Notification.requestPermission().then(permission => {
        if (permission === 'granted') {
          new Notification(`Samwaad: ${title}`, { body: message });
        }
      });
    }
  }

  // Initialize
  function init() {
    console.log('[Samwaad] Initializing extension...');
    
    const panel = createPanel();
    const startBtn = document.getElementById('samwaad-start-btn');
    const stopBtn = document.getElementById('samwaad-stop-btn');

    if (startBtn && stopBtn) {
      startBtn.addEventListener('click', startMonitoring);
      stopBtn.addEventListener('click', stopMonitoring);
      log('✅ Extension ready!', 'success');
    }
  }

  // Wait for DOM and initialize
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
