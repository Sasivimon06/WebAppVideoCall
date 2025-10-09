document.addEventListener('DOMContentLoaded', () => {
    const countdownElement = document.getElementById('countdown');
    const resendBtn = document.getElementById('resendregisterOtp');

    const registerUrl = window.registerUrl; // หน้า register
    let timerId = null;

    // Key สำหรับเก็บค่าเวลาที่หมดอายุใน localStorage
    const localStorageKey = 'otpExpireTimestampRegister';

    // เริ่มนับถอยหลัง
    function startCountdown(expireTimestamp) {
        if (timerId !== null) clearInterval(timerId);
        resendBtn.disabled = true;

        // บันทึกค่าเวลาที่หมดอายุลงใน localStorage
        localStorage.setItem(localStorageKey, expireTimestamp);

        timerId = setInterval(() => {
            const now = Date.now();
            const timeLeftMs = expireTimestamp - now;

            if (timeLeftMs <= 0) {
                clearInterval(timerId);
                countdownElement.textContent = "0:00";
                alert('รหัส OTP หมดอายุ กรุณาขอรหัสใหม่');
                resendBtn.disabled = false;
                window.location.href = registerUrl;
                // ล้างค่าใน localStorage เมื่อหมดอายุ 
                localStorage.removeItem(localStorageKey); 
                return; }

            const totalSeconds = Math.floor(timeLeftMs / 1000);
            const minutes = Math.floor(totalSeconds / 60);
            const seconds = totalSeconds % 60;
            countdownElement.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        }, 1000);
    }

    const savedExpireTimestamp = localStorage.getItem(localStorageKey);
    const initialExpireTimestamp = window.otpExpireTimestampRegister;

    if (savedExpireTimestamp && Number(savedExpireTimestamp) > Date.now()) {
        // ใช้ค่าเก่าจาก localStorage
        startCountdown(Number(savedExpireTimestamp));
    } else if (typeof initialExpireTimestamp !== 'undefined' && initialExpireTimestamp > Date.now()) {
        // ใช้ค่าใหม่จาก server
        startCountdown(initialExpireTimestamp);
    }

    // ------------------------------------------------------------------
    // ปุ่ม resend OTP
    resendBtn.addEventListener('click', (event) => {
        event.preventDefault();
        resendBtn.disabled = true;

        fetch('/resend_register_otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        })
        .then(response => {
            if (!response.ok) return response.json().then(err => Promise.reject(err)); 
            return response.json(); 
        })
        .then(data => {
            if (data.success && data.expire_timestamp) {
                alert('ส่ง OTP สำหรับสมัครสมาชิกเรียบร้อยแล้ว');
                startCountdown(data.expire_timestamp);
            } else {
                alert('ส่ง OTP ใหม่ล้มเหลว: ' + (data.message || 'ไม่ทราบสาเหตุ'));
                resendBtn.disabled = false;
            }
        })
        .catch(err => {
            console.error('Fetch error:', err);
            alert('เกิดข้อผิดพลาดในการส่ง OTP ใหม่: ' + (err.message || JSON.stringify(err)));
            resendBtn.disabled = false;
        });
    });
});
