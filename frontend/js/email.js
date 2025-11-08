document.addEventListener('DOMContentLoaded', () => {
    console.log('📧 Email Page - Loaded');
    loadSentEmails();

    const modal = document.getElementById('emailDetailModal');
    if (modal) {
        modal.onclick = function(event) {
            if (event.target == modal) {
                modal.style.display = "none";
            }
        }
    }
});

let allEmails = [];

async function loadSentEmails() {
    const container = document.getElementById('emailListContainer');
    if (!container) return;

    try {
        container.innerHTML = '<p>Loading emails...</p>';
        const emails = await API.getSentEmails();
        allEmails = emails;
        displayEmails(emails);
    } catch (error)
{
        console.error('❌ Failed to load emails:', error);
        container.innerHTML = `<p style="color: red;">Error loading emails: ${error.message}</p>`;
    }
}

function displayEmails(emails) {
    const container = document.getElementById('emailListContainer');
    if (emails.length === 0) {
        container.innerHTML = '<div class="empty-state" style="padding: 40px;"><div class="empty-state-content"><span class="empty-icon">✉️</span><h3>No Sent Emails</h3><p>Emails you send after a call will appear here.</p></div></div>';
        return;
    }

    container.innerHTML = emails.map((email, index) => {
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = email.body;
        const bodyPreview = tempDiv.textContent || tempDiv.innerText || "";

        return `
            <div class="email-item" onclick="viewEmailDetail(${index})">
                <div class="email-header">
                    <span class="email-recipient">To: ${email.recipient}</span>
                    <span class="email-date">${new Date(email.sent_at).toLocaleString()}</span>
                </div>
                <div class="email-subject">${email.subject}</div>
                <div class="email-body-preview">${bodyPreview.substring(0, 150)}...</div>
            </div>
        `;
    }).join('');
}

function viewEmailDetail(index) {
    const email = allEmails[index];
    if (!email) return;

    const modal = document.getElementById('emailDetailModal');
    const contentDiv = document.getElementById('emailDetailContent');
    
    // Using an iframe is the safest way to render untrusted HTML without style conflicts.
    contentDiv.innerHTML = `
        <h2>${email.subject}</h2>
        <p style="margin-bottom: 5px;"><strong>To:</strong> ${email.recipient}</p>
        <p style="margin-bottom: 20px;"><strong>Sent:</strong> ${new Date(email.sent_at).toLocaleString()}</p>
        <iframe style="width: 100%; height: 60vh; border: 1px solid #e5e5e5;" srcdoc="${email.body.replace(/"/g, '&quot;')}"></iframe>
    `;
    
    modal.style.display = 'block';
}

window.viewEmailDetail = viewEmailDetail;