/**
 * Calendar Page Logic
 * Handles calendar events display, tab switching, and integration with backend
 */

// Global state
let currentTab = 'upcoming';
let calendarEvents = [];
let wsManager = null;

// Initialize calendar page
document.addEventListener('DOMContentLoaded', () => {
    console.log('📅 Calendar Page - Loaded');
    
    // Setup tab switching
    setupTabSwitching();
    
    // Load calendar events
    loadCalendarEvents();
    
    // Check calendar service health
    checkCalendarService();
    
    // Setup WebSocket to listen for new events created via recording
    initializeWebSocketListener();
    
    // Setup copy link functionality
    setupCopyLinkButtons();
});

/**
 * Setup tab switching between Upcoming and Scheduling
 */
function setupTabSwitching() {
    const tabs = document.querySelectorAll('.tab');
    const tabContents = {
        'upcoming': document.getElementById('upcomingTab'),
        'scheduling': document.getElementById('schedulingTab')
    };
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.getAttribute('data-tab');
            
            // Update active tab
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            // Show corresponding content
            Object.keys(tabContents).forEach(key => {
                if (key === tabName) {
                    tabContents[key].classList.add('active');
                    tabContents[key].style.display = 'block';
                } else {
                    tabContents[key].classList.remove('active');
                    tabContents[key].style.display = 'none';
                }
            });
            
            currentTab = tabName;
            console.log(`📑 Switched to ${tabName} tab`);
        });
    });
}

/**
 * Load calendar events from backend
 */
async function loadCalendarEvents() {
    try {
        console.log('📅 Loading calendar events...');
        updateRefreshTime('Loading...');
        
        const events = await API.getCalendarEvents(50);
        calendarEvents = events;
        
        console.log(`✅ Loaded ${events.length} calendar events`);
        displayCalendarEvents(events);
        updateRefreshTime();
        
    } catch (error) {
        console.error('❌ Failed to load calendar events:', error);
        displayCalendarError(error.message);
        updateRefreshTime('Error loading');
    }
}

/**
 * Display calendar events in the table
 */
function displayCalendarEvents(events) {
    const tbody = document.getElementById('calendarEventsBody');
    const paginationTexts = document.querySelectorAll('.pagination-text');
    
    if (!tbody) return;
    
    if (events.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" class="empty-state">
                    <div class="empty-state-content">
                        <span class="empty-icon">📅</span>
                        <h3>No meetings</h3>
                        <p>There are no upcoming meetings to display.</p>
                    </div>
                </td>
            </tr>
        `;
        paginationTexts.forEach(el => el.textContent = '0-0 of 0');
        return;
    }
    
    // Update pagination
    const total = events.length;
    const displayCount = Math.min(25, total);
    paginationTexts.forEach(el => {
        el.textContent = `1-${displayCount} of ${total}`;
    });
    
    // Display events (show first 25)
    tbody.innerHTML = events.slice(0, 25).map(event => {
        const startDate = new Date(event.start);
        const endDate = new Date(event.end);
        
        // Format date
        const dateStr = startDate.toLocaleDateString('en-US', { 
            weekday: 'short', 
            month: 'short', 
            day: 'numeric', 
            year: 'numeric' 
        });
        
        // Format time range
        const startTimeStr = startDate.toLocaleTimeString('en-US', { 
            hour: 'numeric', 
            minute: '2-digit', 
            hour12: true 
        });
        const endTimeStr = endDate.toLocaleTimeString('en-US', { 
            hour: 'numeric', 
            minute: '2-digit', 
            hour12: true 
        });
        
        return `
            <tr data-event-id="${event.id}">
                <td class="col-meeting">
                    <div class="event-meeting-info">
                        <div class="event-title">${escapeHtml(event.summary || 'Untitled Event')}</div>
                        ${event.organizer ? `<div class="event-organizer">Organized by ${escapeHtml(event.organizer)}</div>` : ''}
                    </div>
                </td>
                <td class="col-datetime">
                    <div class="event-datetime">
                        <div class="event-date">${dateStr}</div>
                        <div class="event-time">${startTimeStr} - ${endTimeStr}</div>
                    </div>
                </td>
                <td class="col-addread">
                    <div class="event-actions">
                        ${event.link ? `<a href="${event.link}" target="_blank" class="event-action-btn">Open</a>` : ''}
                    </div>
                </td>
                <td class="col-flexible">
                    <div class="event-actions">
                        <button class="event-action-btn delete" onclick="deleteEvent('${event.id}')">Delete</button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

/**
 * Display error message in calendar table
 */
function displayCalendarError(message) {
    const tbody = document.getElementById('calendarEventsBody');
    if (!tbody) return;
    
    tbody.innerHTML = `
        <tr>
            <td colspan="4" class="empty-state">
                <div class="empty-state-content">
                    <span class="empty-icon">⚠️</span>
                    <h3>Error Loading Events</h3>
                    <p>${escapeHtml(message)}</p>
                    <button class="btn btn-primary" onclick="loadCalendarEvents()" style="margin-top: 16px;">
                        Retry
                    </button>
                </div>
            </td>
        </tr>
    `;
}

/**
 * Delete a calendar event
 */
async function deleteEvent(eventId) {
    if (!confirm('Are you sure you want to delete this event?')) {
        return;
    }
    
    try {
        console.log(`🗑️ Deleting event: ${eventId}`);
        await API.deleteCalendarEvent(eventId);
        
        console.log('✅ Event deleted successfully');
        
        // Remove from local state
        calendarEvents = calendarEvents.filter(e => e.id !== eventId);
        
        // Refresh display
        displayCalendarEvents(calendarEvents);
        
        // Show success message
        alert('Event deleted successfully!');
        
    } catch (error) {
        console.error('❌ Failed to delete event:', error);
        alert(`Failed to delete event: ${error.message}`);
    }
}

/**
 * Check calendar service authentication status
 */
async function checkCalendarService() {
    try {
        const health = await API.checkCalendarHealth();
        
        if (health.authenticated) {
            console.log('✅ Calendar service authenticated');
        } else {
            console.warn('⚠️ Calendar service not authenticated');
            console.warn('Please run authentication flow on backend');
        }
    } catch (error) {
        console.error('❌ Calendar health check failed:', error);
    }
}

/**
 * Update the refresh time display
 */
function updateRefreshTime(text = null) {
    const refreshTimeEl = document.getElementById('calendarRefreshTime');
    if (!refreshTimeEl) return;
    
    if (text) {
        refreshTimeEl.textContent = `🔄 ${text}`;
    } else {
        const now = new Date();
        const timeStr = now.toLocaleTimeString('en-US', { 
            hour: 'numeric', 
            minute: '2-digit', 
            hour12: true 
        });
        refreshTimeEl.textContent = `🔄 Last refreshed at ${timeStr}`;
    }
}

/**
 * Initialize WebSocket listener for new events created via recording
 */
function initializeWebSocketListener() {
    // Note: We don't create a new WebSocket connection here
    // Instead, we listen for messages from the recording page's WebSocket
    // When an event is created via AI during recording, we'll refresh the calendar
    
    // This is a placeholder - in a real app, you'd need to:
    // 1. Share WebSocket connection across pages (use SharedWorker or localStorage events)
    // 2. Or poll the calendar API periodically
    // 3. Or use Server-Sent Events (SSE) for server push
    
    console.log('📡 WebSocket listener initialized (placeholder)');
    
    // For now, we'll just poll every 30 seconds when user is on this page
    setInterval(() => {
        if (currentTab === 'upcoming') {
            console.log('🔄 Auto-refreshing calendar events...');
            loadCalendarEvents();
        }
    }, 30000); // 30 seconds
}

/**
 * Setup copy link functionality for scheduling links
 */
function setupCopyLinkButtons() {
    const copyButtons = document.querySelectorAll('.link-copy-btn');
    
    copyButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            const card = e.target.closest('.scheduling-link-card');
            if (!card) return;
            
            const linkElement = card.querySelector('.link-url');
            if (!linkElement) return;
            
            const url = linkElement.textContent;
            
            // Copy to clipboard
            navigator.clipboard.writeText(url).then(() => {
                // Show success feedback
                const originalHTML = button.innerHTML;
                button.innerHTML = '<span>✓</span>';
                button.style.color = '#34c759';
                
                setTimeout(() => {
                    button.innerHTML = originalHTML;
                    button.style.color = '';
                }, 2000);
                
                console.log(`📋 Copied link: ${url}`);
            }).catch(err => {
                console.error('Failed to copy:', err);
                alert('Failed to copy link to clipboard');
            });
        });
    });
}

/**
 * Utility: Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Make functions globally accessible
window.deleteEvent = deleteEvent;
window.loadCalendarEvents = loadCalendarEvents;
