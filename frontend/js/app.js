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
        tableBody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 40px; color: #86868b;">No calls yet. Start recording!</td></tr>';
        return;
    }
    
    tableBody.innerHTML = calls.map(call => {
        const date = new Date(call.start_time);
        const dateStr = date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
        const timeStr = date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
        
        // Calculate read score (mock data - you can replace with actual logic)
        const readScore = call.sentiment === 'POSITIVE' ? 87 : call.sentiment === 'NEUTRAL' ? 75 : 65;
        
        return `
            <tr>
                <td class="col-source">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 20px;">🎙️</span>
                    </div>
                </td>
                <td class="col-report">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <strong>Call #${call.id}</strong>
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
                <td class="col-owner">
                    <div class="user-avatar" style="width: 28px; height: 28px; font-size: 11px; background: #5a4fb7;">
                        ${call.contact_name ? call.contact_name.substring(0, 2).toUpperCase() : 'AI'}
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function viewCallDetails(callId) {
    // TODO: Implement call details modal
    console.log('View call:', callId);
    alert(`Call details for ID: ${callId}\nThis feature will be implemented soon.`);
}

// Make functions globally accessible
window.startRecording = startRecording;
window.stopRecording = stopRecording;
window.viewCallDetails = viewCallDetails;