// Background service worker for Samwaad Meet Listener
// Simplified - audio capture is now handled in content script

// Handle extension icon click
chrome.action.onClicked.addListener((tab) => {
  // Open popup or focus Meet tab
  if (tab.url && tab.url.includes('meet.google.com')) {
    console.log('[Samwaad BG] Already on Meet tab');
  }
});

// Listen for messages from content script (for future features)
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[Samwaad BG] Message:', message.type);
  
  if (message.type === 'NOTIFICATION') {
    chrome.notifications.create({
      type: 'basic',
      iconUrl: 'icon.png',
      title: message.title || 'Samwaad',
      message: message.message || ''
    });
  }
  
  sendResponse({ success: true });
  return true;
});

console.log('[Samwaad BG] Background service worker loaded');


chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'START_CAPTURE') {
    handleStartCapture(sender.tab.id, message.meetingTitle)
      .then(result => sendResponse({ success: true, ...result }))
      .catch(err => sendResponse({ success: false, error: err.message }));
    return true; // async response
  }

  if (message.type === 'STOP_CAPTURE') {
    handleStopCapture()
      .then(() => sendResponse({ success: true }))
      .catch(err => sendResponse({ success: false, error: err.message }));
    return true;
  }

  if (message.type === 'GET_STATUS') {
    sendResponse({ 
      isCapturing: activeCapture !== null,
      callId: activeCapture?.callId 
    });
    return true;
  }
});

async function handleStartCapture(tabId, meetingTitle) {
  try {
    // Stop any existing capture
    if (activeCapture) {
      await handleStopCapture();
    }

    console.log('[Samwaad BG] Starting capture for tab', tabId);

    // First, check if backend is reachable
    console.log('[Samwaad BG] Checking backend health...');
    try {
      const healthRes = await fetch(`${BACKEND_BASE}/health`, { 
        method: 'GET',
        mode: 'cors'
      });
      if (!healthRes.ok) {
        throw new Error('Backend health check failed');
      }
      console.log('[Samwaad BG] Backend is healthy');
    } catch (healthErr) {
      throw new Error(`Cannot connect to backend at ${BACKEND_BASE}. Please ensure the backend server is running on http://localhost:8000`);
    }

    // Create call in backend
    const callData = await createCall(meetingTitle || 'Google Meet');
    const callId = callData.id;

    console.log('[Samwaad BG] Call created:', callId);

    // Capture tab audio - this captures all audio from the tab including both sides
    const stream = await new Promise((resolve, reject) => {
      chrome.tabCapture.capture(
        { 
          audio: true, 
          video: false 
        },
        (capturedStream) => {
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
          } else if (!capturedStream) {
            reject(new Error('No stream captured - make sure the tab has active audio'));
          } else {
            console.log('[Samwaad BG] Stream captured, tracks:', capturedStream.getTracks().length);
            resolve(capturedStream);
          }
        }
      );
    });

    console.log('[Samwaad BG] Audio stream captured successfully');

    // Connect WebSocket
    const ws = await connectWebSocket(callId);
    
    // Setup audio processing
    const audioContext = new AudioContext({ sampleRate: 48000 });
    const source = audioContext.createMediaStreamSource(stream);
    const processor = audioContext.createScriptProcessor(4096, 1, 1);

    console.log('[Samwaad BG] Audio processing setup complete');

    // Send audio config
    sendAudioConfig(ws, audioContext.sampleRate);

    // Send start recording
    ws.send(JSON.stringify({ type: 'start_recording' }));

    let chunkCount = 0;

    // Process audio and send to backend
    processor.onaudioprocess = (e) => {
      if (ws.readyState !== WebSocket.OPEN) return;
      
      const inputData = e.inputBuffer.getChannelData(0);
      const int16Data = floatTo16BitPCM(inputData);
      
      try {
        ws.send(int16Data.buffer);
        chunkCount++;
        if (chunkCount % 100 === 0) {
          console.log('[Samwaad BG] Sent', chunkCount, 'audio chunks');
        }
      } catch (err) {
        console.error('[Samwaad BG] WS send error:', err);
      }
    };

    source.connect(processor);
    processor.connect(audioContext.destination);

    // Store active capture
    activeCapture = {
      tabId,
      stream,
      ws,
      audioContext,
      source,
      processor,
      callId
    };

    // Setup message handler for notifications
    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        console.log('[Samwaad BG] WS message:', msg.type);

        if (msg.type === 'task_executed') {
          const summary = msg.summary || msg.message || 'AI Task Executed';
          showNotification('AI Action Complete', summary);
          
          // Notify content script
          chrome.tabs.sendMessage(tabId, {
            type: 'TASK_EXECUTED',
            data: msg
          }).catch(() => {});
        }

        if (msg.type === 'call_completed') {
          showNotification('Transcript Ready', 'Call processing completed');
          
          chrome.tabs.sendMessage(tabId, {
            type: 'CALL_COMPLETED',
            data: msg
          }).catch(() => {});
        }
      } catch (e) {
        console.error('[Samwaad BG] Message parse error:', e);
      }
    };

    ws.onerror = (err) => {
      console.error('[Samwaad BG] WebSocket error:', err);
    };

    ws.onclose = () => {
      console.log('[Samwaad BG] WebSocket closed');
    };

    return { callId };

  } catch (err) {
    console.error('[Samwaad BG] Start capture error:', err);
    throw err;
  }
}

async function handleStopCapture() {
  if (!activeCapture) return;

  try {
    console.log('[Samwaad BG] Stopping capture');

    // Send stop message
    if (activeCapture.ws && activeCapture.ws.readyState === WebSocket.OPEN) {
      activeCapture.ws.send(JSON.stringify({ type: 'stop_recording' }));
    }

    // Disconnect audio nodes
    if (activeCapture.processor) {
      activeCapture.processor.disconnect();
      activeCapture.processor.onaudioprocess = null;
    }
    if (activeCapture.source) {
      activeCapture.source.disconnect();
    }
    if (activeCapture.audioContext) {
      await activeCapture.audioContext.close();
    }

    // Stop stream tracks
    if (activeCapture.stream) {
      activeCapture.stream.getTracks().forEach(track => track.stop());
    }

    // Close WebSocket after delay
    setTimeout(() => {
      if (activeCapture?.ws) {
        activeCapture.ws.close();
      }
    }, 1500);

    activeCapture = null;

  } catch (err) {
    console.error('[Samwaad BG] Stop error:', err);
    activeCapture = null;
  }
}

async function createCall(meetingTitle) {
  const payload = {
    platform: 'google_meet',
    contact_name: meetingTitle,
    contact_email: ''
  };

  try {
    const res = await fetch(`${BACKEND_BASE}/api/calls/`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify(payload),
      mode: 'cors'
    });

    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(`Create call failed: ${res.status} - ${errorText}`);
    }

    return await res.json();
  } catch (err) {
    console.error('[Samwaad BG] Create call error:', err);
    throw new Error(`Cannot connect to backend at ${BACKEND_BASE}. Please ensure the backend server is running. Error: ${err.message}`);
  }
}

function connectWebSocket(callId) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(`${WS_BASE}${callId}`);

    ws.onopen = () => {
      console.log('[Samwaad BG] WebSocket connected');
      resolve(ws);
    };

    ws.onerror = (err) => {
      console.error('[Samwaad BG] WebSocket connection error');
      reject(new Error('WebSocket connection failed'));
    };
  });
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
  
  ws.send(JSON.stringify(config));
  // Send duplicate for compatibility
  ws.send(JSON.stringify(config));
}

function floatTo16BitPCM(float32Array) {
  const len = float32Array.length;
  const buffer = new ArrayBuffer(len * 2);
  const view = new DataView(buffer);
  let offset = 0;
  
  for (let i = 0; i < len; i++, offset += 2) {
    const s = Math.max(-1, Math.min(1, float32Array[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
  }
  
  return new Int16Array(buffer);
}

function showNotification(title, message) {
  chrome.notifications.create({
    type: 'basic',
    iconUrl: 'icon.png',
    title: title,
    message: message
  });
}

// Cleanup on extension unload
chrome.runtime.onSuspend.addListener(() => {
  if (activeCapture) {
    handleStopCapture();
  }
});
