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
                const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
                console.log(`🌍 User timezone detected: ${userTimezone}`);
                
                // Send audio configuration AND the new timezone
                this.ws.send(JSON.stringify({
                    type: 'audio_config',
                    sampleRate: audioContext.sampleRate,
                    channels: 1,
                    sampleWidth: 2,
                    isFloat32: false,
                    timezone: userTimezone // ADD THIS LINE
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
                } else if (message.type === 'task_executed') {
                    console.log('✅ Task Executed:', message);
                    alert(`✅ AI Action Complete: ${message.summary}\n\nCheck the Calendar page to see the new event!`);
                    
                    // Trigger custom event for other pages to listen
                    window.dispatchEvent(new CustomEvent('calendarEventCreated', { 
                        detail: message.details 
                    }));
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
             const sentiment = insights.sentiment || { /* ... */ };

            const converter = new showdown.Converter();
            
            const summaryHtml = converter.makeHtml(insights.summary || 'No summary available');
            
            resultsDiv.innerHTML = `
                <div class="results-container">
                    <h2 style="font-size: 24px; margin-bottom: 20px;">${insights.title || 'Meeting Analysis'}</h2>

                    <div class="insights-grid">
                        <div class="insight-card">
                            <h3>💡 AI Summary</h3>
                            <div class="summary-text">
                                ${summaryHtml}
                            </div>
                        </div>

                        <div class="insight-card">
                            <h3>Sentiment Analysis</h3>
                            <div class="sentiment-badge ${sentiment.overall_sentiment.toLowerCase()}">
                                ${sentiment.overall_sentiment}
                            </div>
                            <p><em>${sentiment.reasoning || ''}</em></p>
                        </div>
                    </div>

                    ${insights.chapters && insights.chapters.length > 0 ? `
                        <h3>Chapters</h3>
                        <div class="chapters-container">
                            ${insights.chapters.map(chap => `
                                <div class="chapter-item">
                                    <strong>${chap.title}</strong>: ${chap.summary}
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}

                    <div class="insights-grid">
                        <div class="insight-card">
                            ${insights.action_items && insights.action_items.length > 0 ? `
                                <h3>✅ Action Items</h3>
                                <ul class="action-items">
                                    ${insights.action_items.map(item => `<li><strong>${item.task || 'N/A'}</strong> (Owner: ${item.owner || 'Unassigned'}, Deadline: ${item.deadline || 'N/A'})</li>`).join('')}
                                </ul>
                            ` : '<h3>✅ Action Items</h3><p>No action items detected.</p>'}
                        </div>
                        <div class="insight-card">
                             ${insights.key_decisions && insights.key_decisions.length > 0 ? `
                                <h3>🎯 Key Decisions</h3>
                                <ul class="key-decisions">
                                    ${insights.key_decisions.map(item => `<li>${item}</li>`).join('')}
                                </ul>
                            ` : '<h3>🎯 Key Decisions</h3><p>No key decisions detected.</p>'}
                        </div>
                    </div>
                    
                    ${insights.questions_asked && insights.questions_asked.length > 0 ? `
                        <h3>❓ Key Questions</h3>
                        <ul class="key-questions">
                            ${insights.questions_asked.map(q => `<li>${q}</li>`).join('')}
                        </ul>
                    ` : ''}

                    ${insights.attendees && insights.attendees.length > 0 ? `
                        <h3>👥 Attendees</h3>
                        <p>${insights.attendees.join(', ')}</p>
                    ` : ''}

                    <h3>📝 Full Transcript</h3>
                    <div class="transcript-text">
                        ${transcript.text || 'No speech detected'}
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