document.addEventListener('DOMContentLoaded', () => {
    const countdownElement = document.getElementById('countdown');
    const resendBtn = document.getElementById('resendregisterOtp');

    const registerUrl = window.registerUrl;
    let timerId = null;

    // Key สำหรับเก็บค่าเวลาที่หมดอายุใน localStorage
    const localStorageKey = 'otpExpireTimestampRegister';

    function startCountdown(expireTimestamp) {
    // ถ้ามี timer กำลังทำงานอยู่แล้ว ให้ล้างก่อน
    if (timerId !== null) clearInterval(timerId);

    resendBtn.disabled = true;

    timerId = setInterval(() => {
        const now = Date.now();
        const timeLeftMs = expireTimestamp - now;

        if (timeLeftMs <= 0) {
            clearInterval(timerId);
            timerId = null;
            countdownElement.textContent = "0:00";
            alert('รหัส OTP หมดอายุ กรุณาขอรหัสใหม่');
            resendBtn.disabled = false;
            localStorage.removeItem(localStorageKey);
            return;
        }

        const totalSeconds = Math.floor(timeLeftMs / 1000);
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        countdownElement.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
    }, 1000);

    // เก็บ expire timestamp ล่าสุดลง localStorage
    localStorage.setItem(localStorageKey, expireTimestamp);
}

// ตอนโหลดหน้าเว็บ เริ่มนับถอยหลังถ้ามี expire timestamp จาก server
const initialExpireTimestamp = Number(window.otpExpireTimestampRegister); // มาจาก template
if (initialExpireTimestamp) {
    startCountdown(initialExpireTimestamp);
}

// เมื่อกดส่ง OTP ใหม่
resendBtn.addEventListener('click', (event) => {
    event.preventDefault();
    resendBtn.disabled = true;

    fetch('/resend_register_otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && data.expire_timestamp) {
            alert('ส่ง OTP ใหม่เรียบร้อยแล้ว');
            // เริ่มนับถอยหลังใหม่ทุกครั้ง
            startCountdown(data.expire_timestamp);
        } else {
            alert('ส่ง OTP ใหม่ล้มเหลว: ' + (data.message || 'ไม่ทราบสาเหตุ'));
            resendBtn.disabled = false;
        }
    })
    .catch(err => {
        console.error('Fetch error:', err);
        alert('เกิดข้อผิดพลาดในการส่ง OTP ใหม่');
        resendBtn.disabled = false;
    });
});
});
