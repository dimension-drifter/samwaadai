// Global variables
let wsManager = null;
let currentCallId = null;
let isRecording = false;

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Call Tracker AI - Frontend Loaded');
    
    // Initialize WebSocket Manager
    wsManager = new WebSocketManager();
    
    // Setup event listeners
    setupEventListeners();
    
    // Load initial data
    loadDashboardStats();
    loadRecentCalls();
    
    // Check microphone permissions
    checkMicrophonePermissions();

    // Close modal when clicking outside of it
    const modal = document.getElementById('callDetailModal');
    if (modal) {
        modal.addEventListener('click', (event) => {
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        });
    }
});

function setupEventListeners() {
    // Record button
    const recordBtn = document.getElementById('recordBtn');
    if (recordBtn) {
        recordBtn.addEventListener('click', startRecording);
    }
    
    // Stop button
    const stopBtn = document.getElementById('stopBtn');
    if (stopBtn) {
        stopBtn.addEventListener('click', stopRecording);
    }
    
    // Refresh button
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            loadDashboardStats();
            loadRecentCalls();
        });
    }
}

async function checkMicrophonePermissions() {
    try {
        const result = await navigator.permissions.query({ name: 'microphone' });
        console.log('🎤 Microphone permission:', result.state);
        
        if (result.state === 'denied') {
            alert('Microphone access is denied. Please enable it in your browser settings.');
        }
    } catch (error) {
        console.log('⚠️ Could not check microphone permissions:', error);
    }
}

async function startRecording() {
    try {
        console.log('🎙️ Starting new recording...');
        
        // Disable record button, enable stop button
        const recordBtn = document.getElementById('recordBtn');
        const stopBtn = document.getElementById('stopBtn');
        
        if (recordBtn) recordBtn.disabled = true;
        if (stopBtn) stopBtn.disabled = false;
        
        // Update status
        updateRecordingStatus('🔴 Recording...', 'recording');
        
        // Clear previous results
        const resultsDiv = document.getElementById('transcriptionResults');
        if (resultsDiv) {
            resultsDiv.style.display = 'none';
            resultsDiv.innerHTML = '';
        }
        
        // Create a new call
        const call = await API.createCall({
            platform: 'web',
            contact_name: 'Live Recording',
            contact_email: 'user@example.com'
        });
        
        currentCallId = call.id;
        console.log('✅ Call created:', currentCallId);
        
        // Start WebSocket recording
        await wsManager.startRecording(currentCallId);
        isRecording = true;
        
        console.log('🎤 Recording in progress. Speak now!');
        
    } catch (error) {
        console.error('❌ Failed to start recording:', error);
        alert(`Failed to start recording: ${error.message}`);
        
        // Reset buttons
        const recordBtn = document.getElementById('recordBtn');
        const stopBtn = document.getElementById('stopBtn');
        if (recordBtn) recordBtn.disabled = false;
        if (stopBtn) stopBtn.disabled = true;
        
        updateRecordingStatus('❌ Error starting recording', 'error');
    }
}

function stopRecording() {
    if (!isRecording) {
        console.log('⚠️ Not currently recording');
        return;
    }
    
    console.log('⏹️ Stopping recording...');
    
    // Update status
    updateRecordingStatus('⏳ Processing...', 'processing');
    
    // Disable stop button
    const stopBtn = document.getElementById('stopBtn');
    if (stopBtn) stopBtn.disabled = true;
    
    // Stop WebSocket recording
    wsManager.stopRecording();
    isRecording = false;
    
    console.log('✅ Recording stopped. Processing...');
}

function updateRecordingStatus(message, className) {
    const statusDiv = document.getElementById('recordingStatus');
    if (statusDiv) {
        statusDiv.textContent = message;
        statusDiv.className = `recording-status ${className}`;
        statusDiv.style.display = 'block';
    }
}

async function loadDashboardStats() {
    try {
        console.log('📊 Loading dashboard stats...');
        // This endpoint doesn't exist yet, so we'll skip for now
        // const stats = await API.getAnalytics();
        // updateDashboardUI(stats);
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

async function loadRecentCalls() {
    try {
        console.log('📞 Loading recent calls...');
        const calls = await API.getCalls();
        displayRecentCalls(calls.slice(0, 10)); // Show last 10 calls
    } catch (error) {
        console.error('Failed to load calls:', error);
    }
}

function displayRecentCalls(calls) {
    const tableBody = document.getElementById('callsTableBody');
    if (!tableBody) return;
    
    if (calls.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 40px; color: #86868b;">No calls yet. Start recording!</td></tr>';
        return;
    }
    
    tableBody.innerHTML = calls.map(call => {
        const date = new Date(call.start_time);
        const dateStr = date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
        const timeStr = date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
        
        // Calculate read score (mock data - you can replace with actual logic)
        // Use call.sentiment for better score logic
        const sentiment = (call.sentiment && call.sentiment.overall_sentiment) || 'NEUTRAL';
        const readScore = sentiment === 'POSITIVE' ? 87 : sentiment === 'NEUTRAL' ? 75 : 65;
        
        return `
            <tr onclick="viewCallDetails(${call.id})" style="cursor: pointer;"> 
                <td class="col-source">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 20px;">🎙️</span>
                    </div>
                </td>
                <td class="col-report">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <strong>${call.title || `Call #${call.id}`}</strong>
                        ${call.contact_name && call.contact_name !== 'Live Recording' ? `
                            <span style="color: #86868b;">- ${call.contact_name}</span>
                        ` : ''}
                    </div>
                </td>
                <td class="col-datetime">
                    <div>
                        <div style="font-weight: 500;">${dateStr}</div>
                        <div style="color: #86868b; font-size: 13px;">${timeStr}</div>
                    </div>
                </td>
                <td class="col-score">
                    <div class="read-score">
                        <span class="score-dot" style="background: ${readScore > 80 ? '#34c759' : readScore > 60 ? '#ff9500' : '#ff3b30'};"></span>
                        <span style="font-weight: 600;">${readScore}</span>
                    </div>
                </td>
                <td class="col-folders">
                    <span style="color: #86868b;">—</span>
                </td>
            </tr>
        `;
    }).join('');
}

/**
 * Loads and displays the full details of a specific call in a modal. (NEW FUNCTION)
 * @param {number} callId - The ID of the call to display.
 */
async function viewCallDetails(callId) {
    const modal = document.getElementById('callDetailModal');
    const contentDiv = document.getElementById('callDetailContent');
    
    contentDiv.innerHTML = '<h2 style="color: #5a4fb7;">Loading Call Details...</h2><p>Please wait...</p>';
    modal.style.display = 'block';

    try {
        // Fetch the full call data from the backend
        const call = await API.getCall(callId);
        
        // Initialize Markdown converter (from showdown.min.js in index.html)
        const converter = new showdown.Converter();
        
        // Convert Markdown summary to HTML for display
        const summaryHtml = converter.makeHtml(call.summary || '<em>No summary generated.</em>');
        
        const sentiment = call.sentiment || { overall_sentiment: 'NEUTRAL', reasoning: 'N/A' };
        
        const actionItemsHtml = call.action_items && call.action_items.length > 0
            ? `<ul>${call.action_items.map(item => `<li><strong>${item.task || 'N/A'}</strong> (Owner: ${item.owner || 'Unassigned'}, Deadline: ${item.deadline || 'N/A'})</li>`).join('')}</ul>`
            : '<p>No action items detected.</p>';

        const decisionsHtml = call.key_decisions && call.key_decisions.length > 0
            ? `<ul>${call.key_decisions.map(item => `<li>${item}</li>`).join('')}</ul>`
            : '<p>No key decisions recorded.</p>';
            
        const chaptersHtml = call.chapters && call.chapters.length > 0
            ? `<ul>${call.chapters.map(chap => `<li><strong>${chap.title}</strong>: ${chap.summary}</li>`).join('')}</ul>`
            : '<p>No chapters generated.</p>';

        contentDiv.innerHTML = `
            <h2 style="color: #5a4fb7;">${call.title || `Call #${call.id}`}</h2>
            <p style="font-size: 14px; color: #86868b; margin-bottom: 20px;">
                <strong>Platform:</strong> ${call.platform} | 
                <strong>Start:</strong> ${new Date(call.start_time).toLocaleString()} | 
                <strong>Duration:</strong> ${Math.floor(call.duration_seconds / 60)}m ${call.duration_seconds % 60}s | 
                <strong>Status:</strong> <span class="status-badge ${call.status}">${call.status.replace('_', ' ')}</span>
            </p>

            <h3>💡 AI Summary</h3>
            <div class="detail-section">
                ${summaryHtml}
                <div class="sentiment-badge ${sentiment.overall_sentiment.toLowerCase()}" style="margin-top: 15px;">
                    ${sentiment.overall_sentiment}
                </div>
                <p style="font-size: 13px; color: #5e5e66; margin-top: 5px;"><em>${sentiment.reasoning || 'Reasoning not available.'}</em></p>
            </div>
            
            <div style="display: flex; gap: 20px;">
                <div class="detail-section" style="flex: 1;">
                    <h3>✅ Action Items</h3>
                    ${actionItemsHtml}
                </div>
                <div class="detail-section" style="flex: 1;">
                    <h3>🎯 Key Decisions</h3>
                    ${decisionsHtml}
                </div>
            </div>

            <h3>📚 Meeting Chapters</h3>
            <div class="detail-section">
                ${chaptersHtml}
            </div>

            <h3>📝 Full Transcript</h3>
            <div class="modal-transcript-text">
                ${call.full_transcript_text || '<em>Full transcript not available or speech not detected.</em>'}
            </div>
        `;

    } catch (error) {
        console.error('❌ Failed to fetch call details:', error);
        contentDiv.innerHTML = `
            <h2 style="color: #ff3b30;">Error Loading Details</h2>
            <p>Could not load call details for ID: ${callId}.</p>
            <p>Error: ${error.message}</p>
        `;
    }
}

// Make functions globally accessible
window.startRecording = startRecording;
window.stopRecording = stopRecording;
window.viewCallDetails = viewCallDetails;