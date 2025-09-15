class PatientRegistration {
    constructor(lastPatient) {
        this.lastPatient = lastPatient || null;

        this.bindEvents();
        this.showLastPatient();
    }

    // Bind form submit event
    bindEvents() {
        const form = document.getElementById('patientForm');
        if (form) form.addEventListener('submit', e => this.handleSubmit(e));
    }

    // แสดง summary card ถ้ามีผู้ป่วยล่าสุด
    showLastPatient() {
        if (this.lastPatient) {
            const summaryCard = document.getElementById('formnewPatient');
            const formCard = document.getElementById('formCard');

            if (summaryCard) {
                summaryCard.style.display = 'block';
                summaryCard.innerHTML = `
                    <h3>ข้อมูลผู้ป่วยล่าสุด</h3>
                    <ul>
                        <li><strong>HN:</strong> ${this.lastPatient.HN}</li>
                        <li><strong>ชื่อ-สกุล:</strong> ${this.lastPatient.name}</li>
                        <li><strong>วันเกิด:</strong> ${this.lastPatient.birthDate}</li>
                        <li><strong>เพศ:</strong> ${this.lastPatient.gender}</li>
                        <li><strong>โทรศัพท์:</strong> ${this.lastPatient.phone}</li>
                        <li><strong>โรคประจำตัว:</strong> ${this.lastPatient.disease}</li>
                    </ul>
                `;
            }

            if (formCard) formCard.style.display = 'none';
        }
    }

    // ดึงข้อมูลจาก form และ sanitize
    getSanitizedFormData() {
        const form = document.getElementById('patientForm');
        const formData = new FormData(form);
        return {
            HN: formData.get('HN').trim(),
            name: formData.get('name').trim(),
            birthDate: formData.get('birthDate').trim(),
            gender: formData.get('gender').trim(),
            phone: (formData.get('phone') || '').trim().replace(/'/g, ''),
            disease: (formData.get('disease') || '').trim() || 'ไม่มี'
        };
    }

    // Validate form
    validateForm() {
        const data = this.getSanitizedFormData();
        let isValid = true;
        this.clearErrors();

        if (!data.HN) { this.showError('HNError', 'กรุณากรอกหมายเลข HN'); isValid = false; }
        if (!data.name) { this.showError('nameError', 'กรุณากรอกชื่อ-สกุล'); isValid = false; }
        if (!data.birthDate) { this.showError('birthDateError', 'กรุณาเลือกวันเกิด'); isValid = false; }
        if (!data.gender) { this.showError('genderError', 'กรุณาเลือกเพศ'); isValid = false; }

        return isValid;
    }

    showError(id, msg) {
        const el = document.getElementById(id);
        if (el) el.textContent = msg;
    }

    clearErrors() {
        document.querySelectorAll('.error-message').forEach(el => el.textContent = '');
    }

    // Handle form submit
    async handleSubmit(e) {
        e.preventDefault();

        if (!this.validateForm()) return;

        const data = this.getSanitizedFormData();
        const formData = new FormData();
        Object.keys(data).forEach(key => formData.append(key, data[key]));

        try {
            const res = await fetch('/register_patient', {
                method: 'POST',
                body: formData,
                credentials: 'same-origin'
            });

            const result = await res.json();

            if (!res.ok) {
                alert(result.error || 'เกิดข้อผิดพลาด');
                return;
            }

            this.showSuccessMessage();

            setTimeout(() => {
                window.location.href = '/'; // redirect หลังบันทึก
            }, 2500);

        } catch (err) {
            console.error(err);
            alert('เกิดข้อผิดพลาดในการเชื่อมต่อเซิร์ฟเวอร์');
        }
    }

    // แสดง toast success
    showSuccessMessage() {
        const message = document.createElement('div');
        message.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #10b981;
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 0.5rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 1000;
        `;
        message.textContent = 'บันทึกข้อมูลเรียบร้อยแล้ว!';
        document.body.appendChild(message);

        setTimeout(() => {
            document.body.removeChild(message);
        }, 2500);
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    const patientSystem = new PatientRegistration(window.last_patient);
});
