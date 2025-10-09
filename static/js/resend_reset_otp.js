document.addEventListener('DOMContentLoaded', () => {
    const countdownElement = document.getElementById('countdown');
    const resendBtn = document.getElementById('resendresetOtp');

    const resetUrl = window.resetUrl;
    let timerId = null;

    // Key สำหรับเก็บค่าเวลาที่หมดอายุใน localStorage
    const localStorageKey = 'otpExpireTimestampReset';

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
                window.location.href = resetUrl;
                // ล้างค่าใน localStorage เมื่อหมดอายุ 
                localStorage.removeItem(localStorageKey); 
                return; }

            const totalSeconds = Math.floor(timeLeftMs / 1000);
            const minutes = Math.floor(totalSeconds / 60);
            const seconds = totalSeconds % 60;
            countdownElement.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        }, 1000);
    }

    // โหลดค่าจาก localStorage หรือ server
    const savedExpireTimestamp = localStorage.getItem(localStorageKey);
    // โหลดค่าจาก server เสมอ เพื่อใช้ OTP ใหม่
    const initialExpireTimestamp = window.otpExpireTimestampReset;
    if (typeof initialExpireTimestamp !== 'undefined' && initialExpireTimestamp) {
    // ล้างค่าเก่าใน localStorage
        localStorage.removeItem(localStorageKey);
        startCountdown(initialExpireTimestamp);
    }

    // ------------------------------------------------------------------
    // ปุ่ม resend OTP
    resendBtn.addEventListener('click', (event) => {
        event.preventDefault();
        resendBtn.disabled = true;

        fetch('/resend_reset_otp', {
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
                alert('ส่งรหัส OTP สำหรับรีเซ็ตรหัสผ่านเรียบร้อยแล้ว');
                // เรียก startCountdown ใหม่ เพื่อบันทึกค่าใหม่ลง localStorage
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
