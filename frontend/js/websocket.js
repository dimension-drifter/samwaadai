class WebSocketManager {
    constructor() {
        this.ws = null;
        this.callId = null;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.stream = null;
        this.isRecording = false;
    }

    async startRecording(callId) {
        this.callId = callId;
        this.audioChunks = [];

        try {
            // Request microphone access with specific constraints
            this.stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    sampleRate: 48000,
                    channelCount: 1
                }
            });

            console.log('🎤 Microphone access granted');

            // Create AudioContext for proper audio processing
            const audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: 48000
            });
            
            const source = audioContext.createMediaStreamSource(this.stream);
            const processor = audioContext.createScriptProcessor(4096, 1, 1);

            // Connect WebSocket
            this.ws = new WebSocket(`ws://localhost:8000/ws/call/${callId}`);

            this.ws.onopen = () => {
                console.log('✅ WebSocket connected');
                
                // Send audio configuration
                this.ws.send(JSON.stringify({
                    type: 'audio_config',
                    sampleRate: audioContext.sampleRate,
                    channels: 1,
                    sampleWidth: 2,
                    isFloat32: false
                }));

                // Send start recording message
                this.ws.send(JSON.stringify({
                    type: 'start_recording'
                }));

                this.isRecording = true;

                // Process audio in real-time
                processor.onaudioprocess = (e) => {
                    if (!this.isRecording) return;

                    const inputData = e.inputBuffer.getChannelData(0); // Float32Array
                    
                    // Convert Float32 to Int16 PCM
                    const int16Data = new Int16Array(inputData.length);
                    for (let i = 0; i < inputData.length; i++) {
                        // Clamp to [-1, 1] and convert to 16-bit integer
                        const s = Math.max(-1, Math.min(1, inputData[i]));
                        int16Data[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                    }

                    // Send as binary data
                    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                        this.ws.send(int16Data.buffer);
                    }

                    // Store for debugging
                    this.audioChunks.push(int16Data.buffer.slice(0));
                };

                // Connect the audio processing chain
                source.connect(processor);
                processor.connect(audioContext.destination);

                console.log('🎙️ Recording started...');
                console.log(`   Sample Rate: ${audioContext.sampleRate}Hz`);
                console.log(`   Format: Int16 PCM`);
            };

            this.ws.onmessage = (event) => {
                const message = JSON.parse(event.data);
                console.log('📨 Received:', message.type);

                if (message.type === 'connected') {
                    console.log('✅ Backend ready:', message.message);
                } else if (message.type === 'processing_started') {
                    console.log('⏳ Processing:', message.message);
                    this.showProcessingUI();
                } else if (message.type === 'call_completed') {
                    console.log('✅ Transcription completed!');
                    this.handleTranscriptionComplete(message);
                } else if (message.type === 'error') {
                    console.error('❌ Error:', message.message);
                    alert(`Error: ${message.message}`);
                }
            };

            this.ws.onerror = (error) => {
                console.error('❌ WebSocket error:', error);
                alert('Connection error. Please try again.');
            };

            this.ws.onclose = () => {
                console.log('🔌 WebSocket closed');
                this.cleanup();
            };

        } catch (error) {
            console.error('❌ Microphone access error:', error);
            alert('Could not access microphone. Please check permissions.');
            throw error;
        }
    }

    stopRecording() {
        console.log('⏹️ Stopping recording...');
        this.isRecording = false;

        // Send stop message
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'stop_recording'
            }));
        }

        console.log(`📊 Recorded ${this.audioChunks.length} chunks`);
        const totalBytes = this.audioChunks.reduce((sum, chunk) => sum + chunk.byteLength, 0);
        console.log(`📊 Total audio data: ${totalBytes} bytes`);
    }

    cleanup() {
        // Stop all tracks
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }

        // Close WebSocket
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }

        this.audioChunks = [];
        this.isRecording = false;
        console.log('🧹 Cleanup completed');
    }

    showProcessingUI() {
        const recordBtn = document.getElementById('recordBtn');
        const stopBtn = document.getElementById('stopBtn');
        
        if (recordBtn) recordBtn.disabled = true;
        if (stopBtn) stopBtn.disabled = true;
        
        // Show processing indicator
        const statusDiv = document.getElementById('recordingStatus');
        if (statusDiv) {
            statusDiv.textContent = '⏳ Processing your recording...';
            statusDiv.className = 'recording-status processing';
        }
    }

    handleTranscriptionComplete(message) {
        const { insights, transcript } = message;

        console.log('📝 Transcript:', transcript.text);
        console.log('💡 Summary:', insights.summary);

        // Update UI
        const statusDiv = document.getElementById('recordingStatus');
        if (statusDiv) {
            statusDiv.textContent = '✅ Recording processed!';
            statusDiv.className = 'recording-status completed';
        }

        // Display results
        const resultsDiv = document.getElementById('transcriptionResults');
        if (resultsDiv) {
            resultsDiv.innerHTML = `
                <div class="results-container">
                    <h3>📝 Transcript</h3>
                    <div class="transcript-text">
                        ${transcript.text || 'No speech detected'}
                    </div>
                    
                    <h3>💡 AI Summary</h3>
                    <div class="summary-text">
                        ${insights.summary || 'No summary available'}
                    </div>
                    
                    ${insights.action_items && insights.action_items.length > 0 ? `
                        <h3>✅ Action Items</h3>
                        <ul class="action-items">
                            ${insights.action_items.map(item => `<li>${item}</li>`).join('')}
                        </ul>
                    ` : ''}
                    
                    ${insights.key_decisions && insights.key_decisions.length > 0 ? `
                        <h3>🎯 Key Decisions</h3>
                        <ul class="key-decisions">
                            ${insights.key_decisions.map(item => `<li>${item}</li>`).join('')}
                        </ul>
                    ` : ''}
                    
                    <div class="sentiment-badge ${insights.sentiment.toLowerCase()}">
                        Sentiment: ${insights.sentiment}
                    </div>
                </div>
            `;
            resultsDiv.style.display = 'block';
        }

        // Re-enable buttons
        const recordBtn = document.getElementById('recordBtn');
        const stopBtn = document.getElementById('stopBtn');
        if (recordBtn) recordBtn.disabled = false;
        if (stopBtn) stopBtn.disabled = true;

        // Cleanup
        this.cleanup();
    }
}

// Export for use in app.js
window.WebSocketManager = WebSocketManager;