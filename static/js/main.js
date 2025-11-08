// Utility functions
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    } catch {
        return dateString;
    }
}

function showLoading(element) {
    element.innerHTML = '<div class="flex justify-center items-center py-8"><div class="spinner"></div><span class="ml-2">Loading...</span></div>';
}

function showError(element, message) {
    element.innerHTML = `<div class="bg-red-600 text-white p-4 rounded-lg"><i class="fas fa-exclamation-triangle mr-2"></i>${escapeHtml(message)}</div>`;
}

// API functions
async function apiCall(endpoint, data = null) {
    try {
        const options = {
            method: data ? 'POST' : 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        const response = await fetch(endpoint, options);
        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        return { success: false, error: 'Network error: ' + error.message };
    }
}

// Email functions
async function loadEmails() {
    const tokens = localStorage.getItem('gmail_tokens');
    if (!tokens) {
        alert('Please sign in first');
        return;
    }

    const emailList = document.getElementById('emailList');
    if (!emailList) return;

    showLoading(emailList);

    try {
        const data = await apiCall('/api/emails', { tokens: JSON.parse(tokens) });
        
        if (data.success) {
            displayEmails(data.emails);
            if (data.stats) {
                updateStats(data.stats);
            }
        } else {
            showError(emailList, data.error || 'Failed to load emails');
        }
    } catch (error) {
        showError(emailList, 'Network error: ' + error.message);
    }
}

function displayEmails(emails) {
    const emailList = document.getElementById('emailList');
    if (!emailList) return;

    if (!emails || emails.length === 0) {
        emailList.innerHTML = '<div class="text-center py-8 text-gray-400"><i class="fas fa-inbox text-4xl mb-4"></i><p>No emails found</p></div>';
        return;
    }

    let html = '';
    emails.forEach(email => {
        const snippet = email.snippet.length > 100 ? email.snippet.substring(0, 100) + '...' : email.snippet;
        
        html += `
            <div class="email-card" onclick="viewEmail('${email.id}')">
                <div class="flex justify-between items-start mb-2">
                    <div class="flex-1">
                        <div class="flex items-center justify-between mb-2">
                            <h3 class="font-semibold text-white text-lg">${escapeHtml(email.subject)}</h3>
                            <span class="priority-badge priority-${email.priority}">${email.priority}</span>
                        </div>
                        <p class="text-gray-300 text-sm mb-2"><strong>From:</strong> ${escapeHtml(email.sender)}</p>
                        <p class="text-gray-400 text-sm">${escapeHtml(snippet)}</p>
                    </div>
                </div>
                <div class="flex justify-between items-center mt-3">
                    <div class="flex space-x-2">
                        ${(email.ai_labels || []).map(label => 
                            `<span class="ai-badge">${label}</span>`
                        ).join('')}
                    </div>
                    <span class="text-gray-500 text-sm">${escapeHtml(email.date)}</span>
                </div>
                <div class="flex space-x-2 mt-3">
                    <button class="text-blue-400 hover:text-blue-300 text-sm" onclick="event.stopPropagation(); viewEmailSummary('${email.id}')">
                        <i class="fas fa-robot mr-1"></i>AI Summary
                    </button>
                    <button class="text-green-400 hover:text-green-300 text-sm" onclick="event.stopPropagation(); generateSmartReply('${email.id}')">
                        <i class="fas fa-reply mr-1"></i>Smart Reply
                    </button>
                </div>
            </div>
        `;
    });

    emailList.innerHTML = html;
}

function updateStats(stats) {
    const statsSection = document.getElementById('statsSection');
    if (!statsSection) return;

    statsSection.innerHTML = `
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div class="stats-card">
                <div class="text-2xl font-bold">${stats.total}</div>
                <div class="text-sm opacity-90">Total Emails</div>
            </div>
            <div class="stats-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                <div class="text-2xl font-bold">${stats.work}</div>
                <div class="text-sm opacity-90">Work Priority</div>
            </div>
            <div class="stats-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
                <div class="text-2xl font-bold">${stats.promotions}</div>
                <div class="text-sm opacity-90">Promotions</div>
            </div>
            <div class="stats-card" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
                <div class="text-2xl font-bold">${stats.low}</div>
                <div class="text-sm opacity-90">Low Priority</div>
            </div>
        </div>
    `;
}

function viewEmail(emailId) {
    window.location.href = `/email/${emailId}`;
}

function viewEmailSummary(emailId) {
    window.location.href = `/email/${emailId}/summary`;
}

function generateSmartReply(emailId) {
    window.location.href = `/email/${emailId}/smart-reply`;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Load emails if we're on the inbox page
    if (window.location.pathname === '/inbox') {
        const tokens = localStorage.getItem('gmail_tokens');
        if (tokens) {
            loadEmails();
        }
    }
});
