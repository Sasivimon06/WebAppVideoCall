// static/js/videocall.js

// DOM Elements
const patientForm = document.getElementById('patientForm');
const updateTime = document.getElementById('updateTime');
const messageContainer = document.getElementById('messageContainer');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadFormData();
    updateTimestamp();
    setInterval(updateTimestamp, 1000);
});

// Handle Form Submission
patientForm.addEventListener('submit', async function(e){
    e.preventDefault();

    const data = {
        name: document.getElementById('name').value.trim(),
        HN: document.getElementById('HN').value.trim(),
        followUpDate: document.getElementById('followUpDate').value,
        notes: document.getElementById('notes').value
    };

    // Validate
    if (!data.name || !data.HN) {
        showMessage('กรุณากรอกข้อมูลที่จำเป็น (ชื่อ-สกุล, HN)', 'error');
        return;
    }

    try {
        const response = await fetch('/api/save_patient', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        const result = await response.json();

        if(result.success){
            showMessage(result.message, 'success');
            patientForm.reset();
            localStorage.removeItem('patientFormData'); // ล้าง auto-save
            updateTime.textContent = result.updated_at;
        } else {
            showMessage(result.error || 'เกิดข้อผิดพลาดในการบันทึกข้อมูล', 'error');
        }
    } catch (err) {
        console.error(err);
        showMessage('เกิดข้อผิดพลาดในการเชื่อมต่อเซิร์ฟเวอร์', 'error');
    }
});

// Clear Form
function clearForm() {
    patientForm.reset();
    localStorage.removeItem('patientFormData');
    showMessage('ล้างข้อมูลแล้ว', 'info');
    updateTimestamp();
}

// Auto-save Form Data to localStorage
function autoSaveForm() {
    const formData = {
        name: document.getElementById('name').value,
        HN: document.getElementById('HN').value,
        followUpDate: document.getElementById('followUpDate').value,
        notes: document.getElementById('notes').value
    };
    localStorage.setItem('patientFormData', JSON.stringify(formData));
}

// Load Form Data from localStorage
function loadFormData() {
    const savedData = localStorage.getItem('patientFormData');
    if(savedData){
        const data = JSON.parse(savedData);
        document.getElementById('name').value = data.name || '';
        document.getElementById('HN').value = data.HN || '';
        document.getElementById('followUpDate').value = data.followUpDate || '';
        document.getElementById('notes').value = data.notes || '';
    }
}

// Listen to form changes for auto-save
patientForm.addEventListener('input', autoSaveForm);
patientForm.addEventListener('change', autoSaveForm);

// Update Timestamp
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

// Show Message
function showMessage(text, type = 'success') {
    // สร้าง div message
    const message = document.createElement('div');
    message.className = `top-message ${type}`;
    message.innerHTML = `
        <i class="${type === 'error' ? 'fas fa-exclamation-circle' : type === 'info' ? 'fas fa-info-circle' : 'fas fa-check-circle'}"></i>
        <span>${text}</span>
    `;

    // ใส่ไว้ใน body ด้านบน
    document.body.appendChild(message);

    // แสดงด้วย animation
    setTimeout(() => {
        message.classList.add('show');
    }, 10);

    // หายไปอัตโนมัติ 5 วินาที
    setTimeout(() => {
        message.classList.remove('show');
        setTimeout(() => {
            if (message.parentNode) {
                message.parentNode.removeChild(message);
            }
        }, 500);
    }, 5000);

    // ลบเมื่อคลิก
    message.addEventListener('click', () => {
        message.classList.remove('show');
        setTimeout(() => {
            if (message.parentNode) message.parentNode.removeChild(message);
        }, 500);
    });
}