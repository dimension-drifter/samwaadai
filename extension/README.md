# Samwaad Meet Listener Extension

Chrome extension to capture Google Meet audio and stream to Samwaad AI backend for real-time transcription and calendar automation.

## Setup Instructions

### 1. Start Backend Server

```powershell
cd "c:\1st Hackathon\samwaadai\backend"
.\venv\Scripts\python.exe run.py
```

**Verify backend is running:**
- Open: http://localhost:8000/health
- You should see: `{"status":"healthy",...}`

### 2. Load Extension in Chrome

1. Open Chrome and go to: `chrome://extensions`
2. Enable **"Developer mode"** (toggle in top-right)
3. Click **"Load unpacked"**
4. Select folder: `c:\1st Hackathon\samwaadai\extension`
5. Extension should appear with "Samwaad Meet Listener" name

### 3. Test in Google Meet

1. Join or create a Google Meet: https://meet.google.com
2. Look for the **Samwaad panel** in the **top-right corner** of the Meet page
3. Click **"Start Monitoring"**
4. **IMPORTANT:** When Chrome asks which screen/tab to share:
   - Select **"Tab"** (not Window or Entire Screen)
   - Select **the current Meet tab**
   - ✅ **Check "Share audio"** (this is critical!)
   - Click "Share"
5. Audio from both you and other participants will be captured
6. Click **"Stop"** when finished

## How It Works

The extension uses **`getDisplayMedia()`** API which:
- Prompts user to share a tab/screen with audio
- Captures ALL audio from that tab (your mic + remote participants)
- No special permissions needed beyond user consent
- Works reliably across all Chromium browsers

### Why Not tabCapture?

Initial version used `chrome.tabCapture.capture()` but this API:
- Requires `tabCapture` permission
- Only works in specific contexts (extension pages, not content scripts)
- Has complex permission requirements

The current approach using `getDisplayMedia()` is:
- ✅ More reliable
- ✅ Explicit user consent (better privacy)
- ✅ Works in content scripts
- ✅ No special permissions needed

### Backend Connection
- Extension connects to: `http://localhost:8000`
- WebSocket connects to: `ws://localhost:8000/ws/call/{callId}`
- Make sure backend is running BEFORE starting monitoring

## Troubleshooting

### Error: "Failed to fetch"
**Cause:** Backend is not running or not accessible

**Fix:**
1. Start backend: `python run.py` in backend folder
2. Verify: http://localhost:8000/health should return `{"status":"healthy"}`
3. Reload extension and try again

### Error: "No stream captured"
**Cause:** Meet tab has no active audio

**Fix:**
1. Make sure you're in an active Meet call
2. Unmute your microphone OR wait for others to speak
3. Check Meet tab has audio permission (microphone icon in address bar)

### Error: "Requesting tab audio capture"
**Cause:** Extension needs explicit user action to capture audio

**Fix:**
- This is normal - Chrome requires user interaction (clicking "Start Monitoring" button)
- Make sure you click from the panel injected in the Meet page, not from extension popup

### Panel doesn't appear
**Cause:** Content script not injected or page not refreshed

**Fix:**
1. Go to `chrome://extensions`
2. Find "Samwaad Meet Listener" and click reload icon
3. Refresh Meet tab (Ctrl+R or F5)
4. Panel should appear in top-right corner

### Audio is captured but no transcription
**Cause:** Backend might not have Google Cloud credentials

**Fix:**
1. Check backend logs for errors
2. Verify `backend/credentials.json` exists
3. Check Google Cloud Speech API is enabled
4. Verify backend is processing audio (check logs for "Transcribing...")

### Calendar events not created
**Cause:** Google Calendar credentials not configured

**Fix:**
1. Check `backend/credentials.json` exists
2. Run backend and authenticate with Google Calendar (first time only)
3. Check backend logs for calendar errors

## Debug Mode

### View Background Worker Logs
1. Go to: `chrome://extensions`
2. Find "Samwaad Meet Listener"
3. Click **"service worker"** link
4. DevTools will open showing background script logs

### View Content Script Logs
1. Open Meet tab
2. Press `F12` to open DevTools
3. Go to Console tab
4. Look for logs starting with `[Samwaad]`

### Check Network
1. In DevTools, go to Network tab
2. Start monitoring
3. Look for:
   - POST to `/api/calls/` (should be 200 OK)
   - WebSocket to `/ws/call/{id}` (should upgrade to WS)

## Architecture

```
┌─────────────────┐
│  Google Meet    │
│     (Tab)       │
└────────┬────────┘
         │
         │ Chrome tabCapture API
         │ (captures tab audio)
         ▼
┌─────────────────┐
│ Background.js   │ ← Service Worker
│ (AudioContext)  │   • Creates call via REST
│ (WebSocket)     │   • Opens WebSocket
└────────┬────────┘   • Streams PCM audio
         │
         │ ws://localhost:8000/ws/call/{id}
         ▼
┌─────────────────┐
│ Backend Server  │
│ (FastAPI)       │
│ • STT Service   │ ← Google Cloud Speech
│ • AI Service    │ ← Gemini AI
│ • Calendar Svc  │ ← Google Calendar
└─────────────────┘
```

## Files

- `manifest.json` - Extension manifest (MV3)
- `background.js` - Service worker (audio capture & WebSocket)
- `content.js` - UI injected into Meet page
- `styles.css` - Panel styling
- `popup.html` - Extension popup (informational)
- `icon.png` - Extension icon (placeholder)

## Features

✅ Real-time audio capture from Google Meet (both sides)
✅ Streams to backend via WebSocket
✅ Real-time transcription (Google Cloud Speech)
✅ AI-powered insights (Gemini)
✅ Automatic calendar event creation
✅ Desktop notifications for AI actions
✅ Call tracking in Samwaad dashboard

## Future Enhancements

- [ ] Add Zoom support
- [ ] Add Microsoft Teams support
- [ ] Add pause/resume functionality
- [ ] Show live transcript in panel
- [ ] Add settings UI for backend URL
- [ ] Add proper extension icons
- [ ] Add participant name detection
- [ ] Show calendar event links in panel
