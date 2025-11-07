/**
 * Main Application Logic
 */

// ===================================
// Global State
// ===================================

let currentUser = null;
let currentCallId = null;
let callStartTime = null;
let callDurationInterval = null;

// ===================================
// Initialize App
// ===================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Initializing Call Tracker AI...');
    
    initializeAuth();
    initializeNavigation();
    initializeEventListeners();
    loadDashboard();
});

// ===================================
// Authentication
// ===================================

function initializeAuth() {
    const token = localStorage.getItem('token');
    
    if (!token) {
        // For demo purposes, create a test user
        console.log('⚠️ No token found, using guest mode');
        currentUser = { id: 1, email: 'demo@example.com', name: 'Demo User' };
        document.getElementById('userName').textContent = currentUser.name;
    } else {
        currentUser = { id: 1, email: 'demo@example.com', name: 'Demo User' };
        document.getElementById('userName').textContent = currentUser.name;
    }
}

document.getElementById('logoutBtn')?.addEventListener('click', () => {
    api.logout();
    location.reload();
});

// ===================================
// Navigation
// ===================================

function initializeNavigation() {
    const navButtons = document.querySelectorAll('.nav-btn');
    
    navButtons.forEach(button => {
        button.addEventListener('click', () => {
            const pageName = button.getAttribute('data-page');
            navigateToPage(pageName);
        });
    });
}

function navigateToPage(pageName) {
    // Update active nav button
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-page="${pageName}"]`)?.classList.add('active');
    
    // Show page
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });
    document.getElementById(`${pageName}-page`)?.classList.add('active');
    
    // Load page data
    switch(pageName) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'calls':
            loadCalls();
            break;
        case 'tasks':
            loadTasks();
            break;
        case 'crm':
            loadCRM();
            break;
    }
}

// ===================================
// Event Listeners
// ===================================

function initializeEventListeners() {
    // Start Call Button
    document.getElementById('startCallBtn')?.addEventListener('click', startNewCall);
    
    // Refresh Buttons
    document.getElementById('refreshCallsBtn')?.addEventListener('click', loadCalls);
    
    // Filter Changes
    document.getElementById('callStatusFilter')?.addEventListener('change', (e) => {
        loadCalls(e.target.value);
    });
    
    document.getElementById('taskStatusFilter')?.addEventListener('change', (e) => {
        loadTasks(e.target.value);
    });
    
    // Contact Search
    document.getElementById('contactSearch')?.addEventListener('input', (e) => {
        searchContacts(e.target.value);
    });
    
    // Add Contact Button
    document.getElementById('addContactBtn')?.addEventListener('click', () => {
        openModal('contactModal');
    });
    
    // Contact Form
    document.getElementById('contactForm')?.addEventListener('submit', handleContactSubmit);
    
    // Modal Close Buttons
    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', (e) => {
            closeModal(e.target.closest('.modal').id);
        });
    });
    
    // Recording Controls
    document.getElementById('recordBtn')?.addEventListener('click', startRecording);
    document.getElementById('stopRecordBtn')?.addEventListener('click', stopRecording);
}

// ===================================
// Dashboard
// ===================================

async function loadDashboard() {
    console.log('📊 Loading dashboard...');
    
    try {
        // Load stats
        const stats = await api.getStats();
        
        document.getElementById('totalCalls').textContent = stats.total_calls || 0;
        document.getElementById('completedCalls').textContent = stats.completed_calls || 0;
        document.getElementById('pendingTasks').textContent = stats.pending_tasks || 0;
        document.getElementById('totalContacts').textContent = stats.total_contacts || 0;
        
        // Load recent activity
        const activity = await api.getRecentActivity(10);
        displayRecentActivity(activity);
        
    } catch (error) {
        console.error('Failed to load dashboard:', error);
        showToast('Failed to load dashboard', 'error');
    }
}

function displayRecentActivity(activities) {
    const container = document.getElementById('recentActivity');
    
    if (!activities || activities.length === 0) {
        container.innerHTML = '<p class="empty-state">No recent activity</p>';
        return;
    }
    
    container.innerHTML = activities.map(activity => `
        <div class="call-item">
            <div class="call-item-header">
                <h4>${activity.title || 'Call'}</h4>
                <span class="call-status ${activity.status}">${activity.status}</span>
            </div>
            <div class="call-meta">
                <span><i class="fas fa-calendar"></i> ${formatDate(activity.date)}</span>
                <span><i class="fas fa-clock"></i> ${formatDuration(activity.duration)}</span>
            </div>
        </div>
    `).join('');
}

// ===================================
// Calls Management
// ===================================

async function loadCalls(status = null) {
    console.log('📞 Loading calls...');
    
    try {
        const calls = await api.getCalls(status);
        displayCalls(calls);
    } catch (error) {
        console.error('Failed to load calls:', error);
        showToast('Failed to load calls', 'error');
    }
}

function displayCalls(calls) {
    const container = document.getElementById('callsList');
    
    if (!calls || calls.length === 0) {
        container.innerHTML = '<p class="empty-state">No calls yet. Start your first call!</p>';
        return;
    }
    
    container.innerHTML = calls.map(call => `
        <div class="call-item" onclick="viewCallDetails(${call.id})">
            <div class="call-item-header">
                <h4>Call #${call.id}</h4>
                <span class="call-status ${call.status.replace('_', '-')}">${call.status}</span>
            </div>
            <div class="call-meta">
                <span><i class="fas fa-calendar"></i> ${formatDate(call.start_time)}</span>
                ${call.duration_seconds ? `<span><i class="fas fa-clock"></i> ${formatDuration(call.duration_seconds)}</span>` : ''}
                <span><i class="fas fa-phone"></i> ${call.platform || 'Unknown'}</span>
            </div>
            ${call.summary ? `<p style="margin-top: 10px; color: var(--text-secondary);">${call.summary}</p>` : ''}
        </div>
    `).join('');
}

async function viewCallDetails(callId) {
    try {
        const call = await api.getCall(callId);
        const insights = await api.getCallInsights(callId);
        
        // Display call details in a modal or new page
        console.log('Call details:', call, insights);
        showToast('Call details loaded', 'success');
        
        // TODO: Implement call details view
    } catch (error) {
        console.error('Failed to load call details:', error);
        showToast('Failed to load call details', 'error');
    }
}

// ===================================
// Call Recording
// ===================================

async function startNewCall() {
    try {
        console.log('🎬 Starting new call...');
        
        // Create call in database
        const call = await api.createCall({
            platform: 'web',
            metadata: { source: 'web-app' }
        });
        
        currentCallId = call.id;
        callStartTime = new Date();
        
        console.log('✅ Call created:', call);
        
        // Open call modal
        openModal('callModal');
        
        // Update UI
        document.getElementById('callStartTime').textContent = formatTime(callStartTime);
        document.getElementById('recordBtn').disabled = false;
        document.getElementById('stopRecordBtn').disabled = true;
        
        // Clear previous data
        document.getElementById('liveTranscript').innerHTML = '<p class="transcript-placeholder">Transcript will appear here...</p>';
        document.getElementById('liveActionItems').innerHTML = '<li class="empty">No action items detected yet</li>';
        document.getElementById('liveDecisions').innerHTML = '<li class="empty">No decisions detected yet</li>';
        document.getElementById('liveSentiment').textContent = 'Neutral';
        document.getElementById('liveSentiment').className = 'sentiment-badge neutral';
        
        showToast('Call started! Click record to begin.', 'success');
        
    } catch (error) {
        console.error('Failed to start call:', error);
        showToast('Failed to start call: ' + error.message, 'error');
    }
}

async function startRecording() {
    try {
        console.log('🎤 Starting recording...');
        
        if (!currentCallId) {
            throw new Error('No active call');
        }
        
        // Connect WebSocket
        await wsService.connect(currentCallId);
        
        // Set up WebSocket callbacks
        wsService.on('transcript', handleTranscript);
        wsService.on('insights', handleInsights);
        wsService.on('completed', handleCallCompleted);
        wsService.on('error', handleWebSocketError);
        
        // Start recording
        await wsService.startRecording();
        
        // Update UI
        document.getElementById('recordBtn').disabled = true;
        document.getElementById('stopRecordBtn').disabled = false;
        document.getElementById('recordingStatus').textContent = 'Recording...';
        document.querySelector('.status-dot').classList.add('recording');
        
        // Start duration timer
        startDurationTimer();
        
        showToast('Recording started!', 'success');
        
    } catch (error) {
        console.error('Failed to start recording:', error);
        showToast(error.message, 'error');
    }
}

function stopRecording() {
    console.log('⏹️ Stopping recording...');
    
    wsService.stopRecording();
    
    // Update UI
    document.getElementById('recordBtn').disabled = false;
    document.getElementById('stopRecordBtn').disabled = true;
    document.getElementById('recordingStatus').textContent = 'Processing...';
    document.querySelector('.status-dot').classList.remove('recording');
    
    stopDurationTimer();
    
    showToast('Recording stopped. Processing...', 'info');
}

function handleTranscript(transcript) {
    console.log('📝 Transcript:', transcript);
    
    const container = document.getElementById('liveTranscript');
    
    // Remove placeholder
    if (container.querySelector('.transcript-placeholder')) {
        container.innerHTML = '';
    }
    
    // Add new transcript
    const item = document.createElement('div');
    item.className = 'transcript-item';
    item.innerHTML = `
        <div style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 5px;">
            ${formatTime(new Date())}
        </div>
        <div>${transcript.text}</div>
    `;
    
    container.appendChild(item);
    container.scrollTop = container.scrollHeight;
}

function handleInsights(insights) {
    console.log('💡 Insights:', insights);
    
    // Update action items
    if (insights.action_items && insights.action_items.length > 0) {
        const container = document.getElementById('liveActionItems');
        container.innerHTML = insights.action_items.map(item => `
            <li>
                <strong>${item.task}</strong>
                ${item.person ? `<br><small>Assigned to: ${item.person}</small>` : ''}
                ${item.deadline ? `<br><small>Due: ${item.deadline}</small>` : ''}
            </li>
        `).join('');
    }
    
    // Update decisions
    if (insights.key_decisions && insights.key_decisions.length > 0) {
        const container = document.getElementById('liveDecisions');
        container.innerHTML = insights.key_decisions.map(decision => `
            <li>${decision}</li>
        `).join('');
    }
    
    // Update sentiment
    if (insights.sentiment) {
        const badge = document.getElementById('liveSentiment');
        badge.textContent = insights.sentiment.charAt(0).toUpperCase() + insights.sentiment.slice(1);
        badge.className = `sentiment-badge ${insights.sentiment}`;
    }
}

function handleCallCompleted(finalInsights) {
    console.log('✅ Call completed:', finalInsights);
    
    wsService.disconnect();
    
    // Update UI
    document.getElementById('recordingStatus').textContent = 'Completed';
    document.querySelector('.status-dot').classList.remove('recording');
    
    showToast('Call completed and saved!', 'success');
    
    // Reload dashboard
    loadDashboard();
    
    // Close modal after 3 seconds
    setTimeout(() => {
        closeModal('callModal');
    }, 3000);
}

function handleWebSocketError(error) {
    console.error('WebSocket error:', error);
    showToast('Connection error: ' + error, 'error');
    
    // Reset UI
    document.getElementById('recordBtn').disabled = false;
    document.getElementById('stopRecordBtn').disabled = true;
    document.getElementById('recordingStatus').textContent = 'Error';
    document.querySelector('.status-dot').classList.remove('recording');
    
    stopDurationTimer();
}

// ===================================
// Duration Timer
// ===================================

function startDurationTimer() {
    callDurationInterval = setInterval(() => {
        if (callStartTime) {
            const duration = Math.floor((new Date() - callStartTime) / 1000);
            document.getElementById('callDuration').textContent = formatDuration(duration);
        }
    }, 1000);
}

function stopDurationTimer() {
    if (callDurationInterval) {
        clearInterval(callDurationInterval);
        callDurationInterval = null;
    }
}

// ===================================
// Tasks Management
// ===================================

async function loadTasks(status = null) {
    console.log('📋 Loading tasks...');
    
    try {
        const allTasks = await api.getTasks(status);
        const pendingTasks = await api.getPendingTasks();
        
        displayPendingTasks(pendingTasks);
        displayAllTasks(allTasks);
        
    } catch (error) {
        console.error('Failed to load tasks:', error);
        showToast('Failed to load tasks', 'error');
    }
}

function displayPendingTasks(tasks) {
    const container = document.getElementById('pendingTasksList');
    
    if (!tasks || tasks.length === 0) {
        container.innerHTML = '<p class="empty-state">No tasks pending approval</p>';
        return;
    }
    
    container.innerHTML = tasks.map(task => `
        <div class="task-item">
            <div class="task-item-header">
                <div>
                    <h4>${task.action_type.toUpperCase()}: ${task.title}</h4>
                    <p style="color: var(--text-secondary); margin-top: 5px;">${task.description || 'No description'}</p>
                </div>
                <span class="task-priority ${task.priority}">${task.priority}</span>
            </div>
            <div class="task-actions" style="margin-top: 15px;">
                <button class="btn-success" onclick="approveTask(${task.id})">
                    <i class="fas fa-check"></i> Approve
                </button>
                <button class="btn-danger" onclick="rejectTask(${task.id})">
                    <i class="fas fa-times"></i> Reject
                </button>
            </div>
        </div>
    `).join('');
}

function displayAllTasks(tasks) {
    const container = document.getElementById('allTasksList');
    
    if (!tasks || tasks.length === 0) {
        container.innerHTML = '<p class="empty-state">No tasks yet</p>';
        return;
    }
    
    container.innerHTML = tasks.map(task => `
        <div class="task-item">
            <div class="task-item-header">
                <div>
                    <h4>${task.title}</h4>
                    <p style="color: var(--text-secondary); margin-top: 5px;">
                        ${task.description || 'No description'}
                    </p>
                </div>
                <div style="text-align: right;">
                    <span class="task-priority ${task.priority}">${task.priority}</span>
                    <br>
                    <span class="call-status ${task.status}" style="margin-top: 5px;">${task.status}</span>
                </div>
            </div>
        </div>
    `).join('');
}

async function approveTask(taskId) {
    try {
        await api.approveTask(taskId);
        showToast('Task approved!', 'success');
        loadTasks();
    } catch (error) {
        console.error('Failed to approve task:', error);
        showToast('Failed to approve task', 'error');
    }
}

async function rejectTask(taskId) {
    try {
        await api.rejectTask(taskId);
        showToast('Task rejected', 'info');
        loadTasks();
    } catch (error) {
        console.error('Failed to reject task:', error);
        showToast('Failed to reject task', 'error');
    }
}

// ===================================
// CRM Management
// ===================================

async function loadCRM() {
    console.log('👥 Loading CRM...');
    
    // For demo, show sample contacts
    const sampleContacts = [
        {
            id: 1,
            name: 'John Doe',
            email: 'john@example.com',
            company: 'Acme Corp',
            title: 'CEO',
            last_interaction: new Date().toISOString(),
            interaction_count: 5
        },
        {
            id: 2,
            name: 'Jane Smith',
            email: 'jane@example.com',
            company: 'Tech Inc',
            title: 'CTO',
            last_interaction: new Date().toISOString(),
            interaction_count: 3
        }
    ];
    
    displayContacts(sampleContacts);
}

function displayContacts(contacts) {
    const container = document.getElementById('contactsList');
    
    if (!contacts || contacts.length === 0) {
        container.innerHTML = '<p class="empty-state">No contacts yet</p>';
        return;
    }
    
    container.innerHTML = contacts.map(contact => `
        <div class="contact-item" onclick="viewContact(${contact.id})">
            <div class="contact-header">
                <div class="contact-avatar">
                    ${contact.name.charAt(0).toUpperCase()}
                </div>
                <div class="contact-info">
                    <h4>${contact.name}</h4>
                    <p>${contact.title || 'No title'} ${contact.company ? `at ${contact.company}` : ''}</p>
                </div>
            </div>
            <div class="call-meta" style="margin-top: 10px;">
                <span><i class="fas fa-envelope"></i> ${contact.email || 'No email'}</span>
                <span><i class="fas fa-phone"></i> ${contact.interaction_count || 0} interactions</span>
            </div>
        </div>
    `).join('');
}

function searchContacts(query) {
    // TODO: Implement real search
    console.log('🔍 Searching contacts:', query);
}

function viewContact(contactId) {
    console.log('👤 Viewing contact:', contactId);
    showToast('Contact details coming soon!', 'info');
}
async function startRecording() {
    try {
        console.log('🎤 Starting recording...');
        
        if (!currentCallId) {
            throw new Error('No active call');
        }
        
        // Connect WebSocket
        await wsService.connect(currentCallId);
        
        // Set up WebSocket callbacks
        wsService.on('transcript', handleTranscript);
        wsService.on('insights', handleInsights);
        wsService.on('completed', handleCallCompleted);
        wsService.on('error', handleWebSocketError);
        
        // Send start recording command
        wsService.ws.send(JSON.stringify({
            type: 'start_recording'
        }));
        
        // Start recording audio
        await wsService.startRecording();
        
        // Update UI
        document.getElementById('recordBtn').disabled = true;
        document.getElementById('stopRecordBtn').disabled = false;
        document.getElementById('recordingStatus').textContent = 'Recording...';
        document.querySelector('.status-dot').classList.add('recording');
        
        // Start duration timer
        startDurationTimer();
        
        showToast('Recording started!', 'success');
        
    } catch (error) {
        console.error('Failed to start recording:', error);
        showToast(error.message, 'error');
    }
}
async function handleContactSubmit(e) {
    e.preventDefault();
    
    const contactData = {
        name: document.getElementById('contactName').value,
        email: document.getElementById('contactEmail').value,
        phone: document.getElementById('contactPhone').value,
        company: document.getElementById('contactCompany').value,
        title: document.getElementById('contactTitle').value,
        notes: document.getElementById('contactNotes').value
    };
    
    console.log('💾 Saving contact:', contactData);
    showToast('Contact saved! (Demo mode)', 'success');
    
    closeModal('contactModal');
    document.getElementById('contactForm').reset();
}

// ===================================
// UI Helpers
// ===================================

function openModal(modalId) {
    document.getElementById(modalId)?.classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId)?.classList.remove('active');
}

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatTime(date) {
    return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
        return `${hours}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    }
    return `${minutes}:${String(secs).padStart(2, '0')}`;
}

// ===================================
// Health Check on Load
// ===================================

(async () => {
    try {
        const health = await api.healthCheck();
        console.log('✅ Backend health:', health);
    } catch (error) {
        console.error('⚠️ Backend not available:', error);
        showToast('Warning: Backend server not responding', 'warning');
    }
})();