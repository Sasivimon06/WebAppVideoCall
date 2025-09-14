class PatientRegistration {
    constructor() {
        this.patients = [];
        this.lastPatient = null;
        this.init();
    }

    async init() {
        await this.fetchPatients();   // โหลดข้อมูลผู้ป่วยจาก Flask
        this.bindEvents();
        this.updatePatientCount();
        this.updatePatientList();

        // ถ้ามีผู้ป่วยล่าสุด ให้โชว์ summary card และซ่อน form
        const summaryCard = document.getElementById('summaryCard');
        const formCard = document.getElementById('formCard');

        try {
            const res = await fetch('/register_patient', { method: 'GET', credentials: 'same-origin' });
            if (res.ok) {
                const html = await res.text();
                // ตรวจสอบว่ามี last_patient จาก template
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                const lastPatientData = doc.querySelector('#lastPatientData'); // ใส่ div ซ่อนใน template
                if (lastPatientData) {
                    this.lastPatient = JSON.parse(lastPatientData.textContent);
                    summaryCard.style.display = 'block';
                    formCard.style.display = 'none';
                    this.showPatientCard(this.lastPatient);
                }
            }
        } catch (err) {
            console.error(err);
        }
    }

    bindEvents() {
        const form = document.getElementById('patientForm');
        form.addEventListener('submit', (e) => this.handleSubmit(e));
    }

    getSanitizedFormData() {
        const form = document.getElementById('patientForm');
        let formData = new FormData(form);

        return {
            HN: formData.get('HN').trim(),
            name: formData.get('name').trim(),
            birthDate: formData.get('birthDate').trim(),
            gender: formData.get('gender').trim(),
            phone: formData.get('phone').trim().replace(/'/g, ''), // ลบ ' เกิน
            disease: formData.get('disease').trim() || 'ไม่มี'
        };
    }

    async handleSubmit(e) {
        e.preventDefault();
        if (!this.validateForm()) return;

        const patientData = this.getSanitizedFormData();
        let sanitizedData = new FormData();
        Object.keys(patientData).forEach(key => sanitizedData.append(key, patientData[key]));

        const response = await fetch('/register_patient', {
            method: 'POST',
            body: sanitizedData,
            credentials: 'same-origin'
        });

        if (!response.ok) {
            const err = await response.json();
            alert('เกิดข้อผิดพลาด: ' + (err.error || 'ไม่ทราบสาเหตุ'));
            return;
        }

        const patient = await response.json();
        this.lastPatient = patient;

        // ซ่อน form และโชว์ summary card
        this.lastPatient = patient;
        document.getElementById('formCard').style.display = 'none';
        document.getElementById('summaryCard').style.display = 'block';
        this.showPatientCard(patient);
        this.updatePatientCount();
        this.updatePatientList();
        this.showSuccessMessage();
    }

    showPatientCard(patient) {
        const summaryCard = document.getElementById('summaryCard');
        summaryCard.innerHTML = `
            <h3>ข้อมูลผู้ป่วยล่าสุด</h3>
            <ul>
                <li><strong>HN:</strong> ${patient.HN}</li>
                <li><strong>ชื่อ-สกุล:</strong> ${patient.name}</li>
                <li><strong>วันเกิด:</strong> ${this.formatDate(patient.birthDate)}</li>
                <li><strong>เพศ:</strong> ${this.getGenderText(patient.gender)}</li>
                <li><strong>โทรศัพท์:</strong> ${patient.phone}</li>
                <li><strong>โรคประจำตัว:</strong> ${patient.disease}</li>
            </ul>
        `;
    }


    async fetchPatients() {
        try {
            const response = await fetch('/patients', { credentials: 'same-origin' });
            if (!response.ok) throw new Error("โหลดรายชื่อผู้ป่วยล้มเหลว");
            this.patients = await response.json();
        } catch (err) {
            console.error(err);
            this.patients = [];
        }
    }

    updatePatientCount() {
        const count = this.patients.length;
        const el = document.getElementById('patientCount');
        if (el) el.textContent = count;
    }

    updatePatientList() {
        const tableBody = document.getElementById('patientTableBody');
        if (!tableBody) return;
        tableBody.innerHTML = "";
        this.patients.forEach(p => {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${p.HN}</td>
                <td>${p.name}</td>
                <td>${this.formatDate(p.birthDate)}</td>
                <td>${this.getGenderText(p.gender)}</td>
                <td>${p.phone}</td>
                <td>${p.disease}</td>
            `;
            tableBody.appendChild(row);
        });
    }

    validateForm() {
        const data = this.getSanitizedFormData();
        let isValid = true;
        this.clearErrors();

        if (!data.HN) { this.showError('HNError', 'กรุณากรอกหมายเลข HN'); isValid = false; }
        if (!data.name) { this.showError('nameError', 'กรุณากรอกชื่อ-สกุล'); isValid = false; }
        if (!data.birthDate) { this.showError('birthDateError', 'กรุณาเลือกวันเกิด'); isValid = false; }
        if (!data.gender) { this.showError('genderError', 'กรุณาเลือกเพศ'); isValid = false; }
        if (!data.phone) { this.showError('phoneError', 'กรุณากรอกเบอร์โทรศัพท์'); isValid = false; }

        return isValid;
    }

    showError(elementId, message) {
        const el = document.getElementById(elementId);
        if(el) el.textContent = message;
    }

    clearErrors() {
        document.querySelectorAll('.error-message').forEach(el => el.textContent = '');
    }

    resetForm() {
        document.getElementById('patientForm').reset();
        this.clearErrors();
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('th-TH', {year:'numeric', month:'long', day:'numeric'});
    }

    getGenderText(gender) {
        switch(gender){
            case 'male': return 'ชาย';
            case 'female': return 'หญิง';
            case 'other': return 'อื่นๆ';
            default: return gender;
        }
    }

    showSuccessMessage() {
        const message = document.createElement('div');
        message.style.cssText = `position:fixed; top:20px; right:20px; background:#10b981; color:white; padding:1rem 1.5rem; border-radius:0.5rem; box-shadow:0 4px 12px rgba(0,0,0,0.15); z-index:1000;`;
        message.textContent = 'บันทึกข้อมูลเรียบร้อยแล้ว!';
        document.body.appendChild(message);

        setTimeout(() => {
            document.body.removeChild(message);
        }, 3000);
    }
}

// Initialize
const patientSystem = new PatientRegistration();
