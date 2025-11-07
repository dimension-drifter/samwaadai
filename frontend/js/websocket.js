/**
 * WebSocket Service - Handles real-time call recording
 */

class WebSocketService {
    constructor() {
        this.ws = null;
        this.callId = null;
        this.mediaRecorder = null;
        this.audioStream = null;
        this.callbacks = {};
    }

    /**
     * Connect to WebSocket for a call
     */
    connect(callId) {
        return new Promise((resolve, reject) => {
            this.callId = callId;
            const wsUrl = `${WS_BASE_URL}/ws/call/${callId}`;

            console.log('Connecting to WebSocket:', wsUrl);

            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                console.log('✅ WebSocket connected');
                resolve();
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };

            this.ws.onerror = (error) => {
                console.error('❌ WebSocket error:', error);
                reject(error);
            };

            this.ws.onclose = () => {
                console.log('👋 WebSocket disconnected');
                this.cleanup();
                if (this.callbacks.onClose) {
                    this.callbacks.onClose();
                }
            };
        });
    }

    /**
     * Handle incoming WebSocket messages
     */
    handleMessage(data) {
        console.log('📨 WebSocket message:', data);

        switch (data.type) {
            case 'connected':
                if (this.callbacks.onConnected) {
                    this.callbacks.onConnected(data);
                }
                break;

            case 'transcript':
                if (this.callbacks.onTranscript) {
                    this.callbacks.onTranscript(data.data);
                }
                break;

            case 'partial_insights':
                if (this.callbacks.onPartialInsights) {
                    this.callbacks.onPartialInsights(data.data);
                }
                break;

            case 'call_completed':
                if (this.callbacks.onCallCompleted) {
                    this.callbacks.onCallCompleted(data.insights);
                }
                break;

            case 'error':
                console.error('WebSocket error:', data.message);
                if (this.callbacks.onError) {
                    this.callbacks.onError(data.message);
                }
                break;

            default:
                console.log('Unknown message type:', data.type);
        }
    }

    /**
     * Register callbacks for WebSocket events
     */
    on(event, callback) {
        const eventMap = {
            'connected': 'onConnected',
            'transcript': 'onTranscript',
            'insights': 'onPartialInsights',
            'completed': 'onCallCompleted',
            'error': 'onError',
            'close': 'onClose'
        };

        const callbackName = eventMap[event];
        if (callbackName) {
            this.callbacks[callbackName] = callback;
        }
    }

    /**
     * Start recording audio from microphone
     */
    async startRecording() {
        try {
            // Request microphone access
            this.audioStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    sampleRate: 16000
                }
            });

            console.log('🎤 Microphone access granted');

            // Create MediaRecorder
            const options = {
                mimeType: 'audio/webm;codecs=opus'
            };

            // Fallback for browsers that don't support webm
            if (!MediaRecorder.isTypeSupported(options.mimeType)) {
                options.mimeType = 'audio/ogg;codecs=opus';
                if (!MediaRecorder.isTypeSupported(options.mimeType)) {
                    options.mimeType = 'audio/wav';
                }
            }

            this.mediaRecorder = new MediaRecorder(this.audioStream, options);

            // Handle audio data
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0 && this.ws && this.ws.readyState === WebSocket.OPEN) {
                    // Send audio data to backend
                    this.ws.send(event.data);
                    console.log('📤 Sent audio chunk:', event.data.size, 'bytes');
                }
            };

            // Start recording (send chunks every 250ms)
            this.mediaRecorder.start(250);

            console.log('✅ Recording started');
            return true;

        } catch (error) {
            console.error('❌ Failed to start recording:', error);
            
            // User-friendly error messages
            if (error.name === 'NotAllowedError') {
                throw new Error('Microphone access denied. Please allow microphone access and try again.');
            } else if (error.name === 'NotFoundError') {
                throw new Error('No microphone found. Please connect a microphone and try again.');
            } else {
                throw new Error('Failed to start recording: ' + error.message);
            }
        }
    }

    /**
     * Stop recording
     */
    stopRecording() {
        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
            this.mediaRecorder.stop();
            console.log('⏹️ Recording stopped');
        }

        // Send stop message to backend
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'stop_recording'
            }));
        }

        this.cleanup();
    }

    /**
     * Disconnect WebSocket
     */
    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        this.cleanup();
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        // Stop media recorder
        if (this.mediaRecorder) {
            if (this.mediaRecorder.state !== 'inactive') {
                this.mediaRecorder.stop();
            }
            this.mediaRecorder = null;
        }

        // Stop audio stream
        if (this.audioStream) {
            this.audioStream.getTracks().forEach(track => track.stop());
            this.audioStream = null;
        }
    }
}

// Export singleton instance
const wsService = new WebSocketService();