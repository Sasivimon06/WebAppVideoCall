// Password visibility toggle
function togglePassword() {
    const passwordInput = document.getElementById('password');
    const eyeIcon = document.getElementById('eyeIcon');
    
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        eyeIcon.classList.remove('fa-eye');
        eyeIcon.classList.add('fa-eye-slash');
    } else {
        passwordInput.type = 'password';
        eyeIcon.classList.remove('fa-eye-slash');
        eyeIcon.classList.add('fa-eye');
    }
}

// confirm password
function toggleConfirmPassword() {
    const passwordInput = document.getElementById('confirm_password');
    const eyeIcon = document.getElementById('eyeIconConfirm');

    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        eyeIcon.src = EYE_OFF_ICON; // ตาปิด
    } else {
        passwordInput.type = 'password';
        eyeIcon.src = EYE_ICON; // ตาเปิด
    }
}


// Form submission with loading state
document.getElementById('loginForm').addEventListener('submit', function(e) {
    const submitBtn = document.getElementById('submitBtn');
    const btnText = document.getElementById('btnText');
    const loadingSpinner = document.getElementById('loadingSpinner');
    
    // Show loading state
    submitBtn.disabled = true;
    btnText.style.display = 'none';
    loadingSpinner.style.display = 'block';
    
    // Let the form submit naturally to Flask
    // The loading state will be visible until the page reloads
});

// Flash message system (for dynamically added messages)
function showFlashMessage(type, message) {
    const flashContainer = document.getElementById('flashMessages');
    
    if (!flashContainer) {
        // Create flash container if it doesn't exist
        const newContainer = document.createElement('div');
        newContainer.id = 'flashMessages';
        newContainer.className = 'flash-messages';
        document.querySelector('.login-card').appendChild(newContainer);
    }
    
    const flashDiv = document.createElement('div');
    flashDiv.className = `flash-message ${type}`;
    flashDiv.textContent = message;
    
    flashContainer.appendChild(flashDiv);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        flashDiv.style.opacity = '0';
        setTimeout(() => {
            if (flashDiv.parentNode) {
                flashDiv.parentNode.removeChild(flashDiv);
            }
        }, 300);
    }, 5000);
}

// Initialize particles with random positions
document.addEventListener('DOMContentLoaded', function() {
    const particles = document.querySelectorAll('.particle');
    particles.forEach(particle => {
        particle.style.left = Math.random() * 100 + '%';
        particle.style.top = Math.random() * 100 + '%';
        particle.style.animationDelay = Math.random() * 5 + 's';
    });
    
    // Auto-hide flash messages after 5 seconds
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.opacity = '0';
            setTimeout(() => {
                if (message.parentNode) {
                    message.parentNode.removeChild(message);
                }
            }, 300);
        }, 5000);
    });
});

// Add smooth focus transitions
document.querySelectorAll('input').forEach(input => {
    input.addEventListener('focus', function() {
        this.style.transform = 'translateY(-1px)';
    });
    
    input.addEventListener('blur', function() {
        this.style.transform = 'translateY(0)';
    });
});

// Enhanced button interactions
document.querySelectorAll('button').forEach(button => {
    button.addEventListener('mousedown', function() {
        if (!this.disabled) {
            this.style.transform = 'translateY(1px)';
        }
    });
    
    button.addEventListener('mouseup', function() {
        if (!this.disabled) {
            this.style.transform = 'translateY(-2px)';
        }
    });
    
    button.addEventListener('mouseleave', function() {
        if (!this.disabled) {
            this.style.transform = 'translateY(0)';
        }
    });
});