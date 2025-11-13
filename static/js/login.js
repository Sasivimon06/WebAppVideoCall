// Password visibility toggle
function togglePassword() {
    const passwordInput = document.getElementById('password');
    const eyeIcon = document.getElementById('eyeIcon');
    
    if (passwordInput && eyeIcon) {
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
}

// Confirm password visibility toggle
function toggleConfirmPassword() {
    const passwordInput = document.getElementById('confirm_password');
    const eyeIcon = document.getElementById('eyeIconConfirm');

    if (passwordInput && eyeIcon) {
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
}

// ✅ รอให้หน้าเว็บโหลดครบก่อนแล้วค่อยผูก Event ทั้งหมด
document.addEventListener('DOMContentLoaded', function() {

    // Form submission with loading state
    const loginForm = document.getElementById('loginFormElement');
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            const submitBtn = document.getElementById('submitBtn');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.classList.add('loading');
            }
        });
    }

    // Flash message system (for dynamically added messages)
    function showFlashMessage(type, message) {
        const flashContainer = document.getElementById('flashMessages');
        
        if (!flashContainer) {
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
});
