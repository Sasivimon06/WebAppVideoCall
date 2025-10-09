// Main JavaScript functionality
document.addEventListener('DOMContentLoaded', function() {
    // Initialize application
    initializeApp();
    
    // Add smooth scrolling to navigation links
    addSmoothScrolling();
    
    // Initialize intersection observer for animations
    initializeAnimations();
});

function initializeApp() {
    console.log('🏥 ระบบดูแลสุขภาพ - เริ่มต้นแล้ว');
    
    // Add loading states to buttons
    const buttons = document.querySelectorAll('.btn, .call-btn');
    buttons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!this.disabled) {
                addLoadingState(this);
            }
        });
    });
    
    // Add hover effects to cards
    const cards = document.querySelectorAll('.service-card, .patient-card, .category-card');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
}

function addLoadingState(button) {
    const originalText = button.textContent;
    button.textContent = 'กำลังโหลด...';
    button.disabled = true;
    
    setTimeout(() => {
        button.textContent = originalText;
        button.disabled = false;
    }, 1500);
}

function addSmoothScrolling() {
    const links = document.querySelectorAll('a[href^="#"]');
    
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            const targetSection = document.querySelector(targetId);
            
            if (targetSection) {
                targetSection.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

function initializeAnimations() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    });
    
    const animatedElements = document.querySelectorAll('.service-card, .content-item, .patient-card');
    
    animatedElements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = 'all 0.6s ease-out';
        observer.observe(el);
    });
}

// Utility functions
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    // Add styles
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? '#22c55e' : type === 'error' ? '#ef4444' : '#667eea'};
        color: white;
        padding: 1rem 2rem;
        border-radius: 10px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.2);
        z-index: 1000;
        transform: translateX(100%);
        transition: transform 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => {
        notification.style.transform = 'translateX(0)';
    }, 100);
    
    // Auto remove
    setTimeout(() => {
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 3000);
}

function formatDateTime(date) {
    return new Date(date).toLocaleString('th-TH', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Export functions for use in other scripts
window.AppUtils = {
    showNotification,
    formatDateTime,
    addLoadingState
};

// Service Worker registration (for offline functionality)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('/static/js/sw.js')
            .then(function(registration) {
                console.log('SW registered: ', registration);
            }, function(registrationError) {
                console.log('SW registration failed: ', registrationError);
            });
    });
}

// Handle offline/online status
window.addEventListener('online', function() {
    showNotification('เชื่อมต่ออินเทอร์เน็ตแล้ว', 'success');
});

window.addEventListener('offline', function() {
    showNotification('การเชื่อมต่ออินเทอร์เน็ตขาดหาย', 'error');
});

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Alt + H: Go to home
    if (e.altKey && e.key === 'h') {
        window.location.href = '/';
    }
    
    // Alt + E: Go to education
    if (e.altKey && e.key === 'e') {
        window.location.href = '/education';
    }
    
    // Alt + V: Go to video call
    if (e.altKey && e.key === 'v') {
        window.location.href = '/video-call';
    }
});

// Performance monitoring
window.addEventListener('load', function() {
    const loadTime = performance.now();
    console.log(`⏱️ หน้าเว็บโหลดเสร็จใน ${Math.round(loadTime)} ms`);
    
    if (loadTime > 3000) {
        console.warn('⚠️ หน้าเว็บโหลดช้า อาจต้องปรับปรุงประสิทธิภาพ');
    }
});