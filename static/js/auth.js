// Authentication functions
function checkAuth() {
    const user = localStorage.getItem('user_email');
    const tokens = localStorage.getItem('gmail_tokens');
    
    if (user && tokens) {
        // Update UI for signed-in state
        const userInfo = document.getElementById('userInfo');
        const logoutBtn = document.getElementById('logoutBtn');
        
        if (userInfo) {
            userInfo.classList.remove('hidden');
            document.getElementById('userEmail').textContent = user;
        }
        if (logoutBtn) {
            logoutBtn.classList.remove('hidden');
        }
        return true;
    }
    return false;
}

function logout() {
    localStorage.removeItem('user_email');
    localStorage.removeItem('gmail_tokens');
    localStorage.removeItem('user_name');
    window.location.href = '/';
}

function requireAuth() {
    if (!checkAuth()) {
        alert('Please sign in to access this feature');
        window.location.href = '/auth';
        return false;
    }
    return true;
}

// Initialize auth check on page load
document.addEventListener('DOMContentLoaded', function() {
    checkAuth();
    
    // Set active navigation item
    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-item').forEach(item => {
        if (item.getAttribute('href') === currentPath) {
            item.classList.add('active');
        }
    });
});
