// Application State
let appState = {
    isCallActive: false,
    isMicOn: true,
    isVideoOn: true,
    patientData: {
        firstName: '',
        lastName: '',
        hn: '',
        notes: '',
        followUpDate: '',
        status: 'pending'
    }
};

// DOM Elements
const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const micBtn = document.getElementById('micBtn');
const videoBtn = document.getElementById('videoBtn');
const callBtn = document.getElementById('callBtn');
const micIcon = document.getElementById('micIcon');
const videoIcon = document.getElementById('videoIcon');
const callIcon = document.getElementById('callIcon');
const callText = document.getElementById('callText');
const hostVideoOff = document.getElementById('hostVideoOff');
const patientForm = document.getElementById('patientForm');
const updateTime = document.getElementById('updateTime');
const messageContainer = document.getElementById('messageContainer');

// Initialize Application
document.addEventListener('DOMContentLoaded', function() {
    updateTimestamp();
    setInterval(updateTimestamp, 1000);
    
    // Form submission
    patientForm.addEventListener('submit', handleFormSubmit);
    
    // Load existing patients (if any)
    loadPatients();
});

// Video Call Functions
function toggleCall() {
    appState.isCallActive = !appState.isCallActive;
    
    if (appState.isCallActive) {
        startCall();
    } else {
        endCall();
    }
    
    updateCallUI();
}

function startCall() {
    statusDot.classList.add('connected');
    statusText.textContent = 'Connected';
    callBtn.classList.add('active');
    callIcon.className = 'fas fa-phone-slash';
    callText.textContent = 'End Call';
    
    showMessage('เริ่มการโทรวิดีโอแล้ว', 'success');
}

function endCall() {
    statusDot.classList.remove('connected');
    statusText.textContent = 'Not Connected';
    callBtn.classList.remove('active');
    callIcon.className = 'fas fa-phone';
    callText.textContent = 'Start Video Call';
    
    showMessage('จบการโทรวิดีโอแล้ว', 'info');
}

function toggleMic() {
    appState.isMicOn = !appState.isMicOn;
    
    if (appState.isMicOn) {
        micBtn.classList.remove('muted');
        micIcon.className = 'fas fa-microphone';
    } else {
        micBtn.classList.add('muted');
        micIcon.className = 'fas fa-microphone-slash';
    }
    
    showMessage(appState.isMicOn ? 'เปิดไมโครโฟนแล้ว' : 'ปิดไมโครโฟนแล้ว', 'info');
}

function toggleVideo() {
    appState.isVideoOn = !appState.isVideoOn;
    
    if (appState.isVideoOn) {
        videoBtn.classList.remove('muted');
        videoIcon.className = 'fas fa-video';
        hostVideoOff.style.display = 'none';
    } else {
        videoBtn.classList.add('muted');
        videoIcon.className = 'fas fa-video-slash';
        hostVideoOff.style.display = 'flex';
    }
    
    showMessage(appState.isVideoOn ? 'เปิดกล้องแล้ว' : 'ปิดกล้องแล้ว', 'info');
}

function updateCallUI() {
    // Update UI based on call state
    const controls = document.querySelectorAll('.control-btn');
    controls.forEach(btn => {
        btn.disabled = !appState.isCallActive && btn !== callBtn;
    });
}

// Form Functions
async function handleFormSubmit(e) {
    e.preventDefault();
    
    const formData = new FormData(patientForm);
    const patientData = {
        firstName: formData.get('firstName'),
        lastName: formData.get('lastName'),
        hn: formData.get('hn'),
        notes: formData.get('notes'),
        followUpDate: formData.get('followUpDate'),
        status: formData.get('status')
    };
    
    // Validate required fields
    if (!patientData.firstName || !patientData.lastName || !patientData.hn) {
        showMessage('กรุณากรอกข้อมูลที่จำเป็น (ชื่อ, นามสกุล, HN)', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/patients', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(patientData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage(result.message, 'success');
            appState.patientData = patientData;
            updateTimestamp();
        } else {
            showMessage(result.error || 'เกิดข้อผิดพลาดในการบันทึกข้อมูล', 'error');
        }
    } catch (error) {
        console.error('Error saving patient:', error);
        showMessage('เกิดข้อผิดพลาดในการเชื่อมต่อเซิร์ฟเวอร์', 'error');
    }
}

function clearForm() {
    patientForm.reset();
    appState.patientData = {
        firstName: '',
        lastName: '',
        hn: '',
        notes: '',
        followUpDate: '',
        status: 'pending'
    };
    
    showMessage('ล้างข้อมูลแล้ว', 'info');
    updateTimestamp();
}

async function loadPatients() {
    try {
        const response = await fetch('/api/patients');
        const patients = await response.json();
        
        if (patients.length > 0) {
            console.log('Loaded patients:', patients);
        }
    } catch (error) {
        console.error('Error loading patients:', error);
    }
}

// Utility Functions
function updateTimestamp() {
    const now = new Date();
    const thaiTime = now.toLocaleString('th-TH', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    
    updateTime.textContent = thaiTime;
}

function showMessage(text, type = 'success') {
    const message = document.createElement('div');
    message.className = `message ${type}`;
    
    const iconClass = type === 'error' ? 'fas fa-exclamation-circle' : 
                     type === 'info' ? 'fas fa-info-circle' : 
                     'fas fa-check-circle';
    
    message.innerHTML = `
        <div class="message-content">
            <i class="${iconClass} message-icon"></i>
            <span class="message-text">${text}</span>
        </div>
    `;
    
    messageContainer.appendChild(message);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (message.parentNode) {
            message.parentNode.removeChild(message);
        }
    }, 5000);
    
    // Remove on click
    message.addEventListener('click', () => {
        if (message.parentNode) {
            message.parentNode.removeChild(message);
        }
    });
}

// Keyboard Shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + Enter to save form
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        patientForm.dispatchEvent(new Event('submit'));
    }
    
    // Space to toggle call (when not in input)
    if (e.code === 'Space' && !e.target.matches('input, textarea, select')) {
        e.preventDefault();
        toggleCall();
    }
    
    // M to toggle mic
    if (e.key.toLowerCase() === 'm' && !e.target.matches('input, textarea, select')) {
        e.preventDefault();
        toggleMic();
    }
    
    // V to toggle video
    if (e.key.toLowerCase() === 'v' && !e.target.matches('input, textarea, select')) {
        e.preventDefault();
        toggleVideo();
    }
});

// Auto-save form data to localStorage
function autoSaveForm() {
    const formData = new FormData(patientForm);
    const data = {};
    for (let [key, value] of formData.entries()) {
        data[key] = value;
    }
    localStorage.setItem('patientFormData', JSON.stringify(data));
}

// Load form data from localStorage
function loadFormData() {
    const savedData = localStorage.getItem('patientFormData');
    if (savedData) {
        const data = JSON.parse(savedData);
        Object.keys(data).forEach(key => {
            const element = document.getElementById(key);
            if (element) {
                element.value = data[key];
            }
        });
    }
}

// Auto-save on form change
patientForm.addEventListener('input', autoSaveForm);
patientForm.addEventListener('change', autoSaveForm);

// Load saved data on page load
document.addEventListener('DOMContentLoaded', loadFormData);