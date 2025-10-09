// ---------------------
// DOM Elements
// ---------------------
const localVideo = document.getElementById('hostVideo');
const remoteVideo = document.getElementById('patientVideo');
const statusText = document.getElementById('statusText');
const statusDot = document.getElementById('statusDot');

const micBtn = document.getElementById('micBtn');
const videoBtn = document.getElementById('videoBtn');
const callBtn = document.getElementById('callBtn');
const endCallBtn = document.getElementById('endCallBtn');
const hnInput = document.getElementById('HN');
<<<<<<< HEAD
const nameInput = document.getElementById('name');
const patientForm = document.getElementById('patientForm');
=======
>>>>>>> a5d1bc9f89d7de9335090e1327c095d68c2013a6

const socket = io();
let localStream = null;
let peerConnection = null;
let isCallActive = false;
<<<<<<< HEAD
let currentRoom = null;
=======
>>>>>>> a5d1bc9f89d7de9335090e1327c095d68c2013a6

// ICE Config
const config = {
    iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
<<<<<<< HEAD
        { urls: 'stun:stun1.l.google.com:19302' },
=======
>>>>>>> a5d1bc9f89d7de9335090e1327c095d68c2013a6
        { urls: 'turn:openrelay.metered.ca:80', username: 'openrelay', credential: 'openrelay' }
    ]
};

// ---------------------
<<<<<<< HEAD
// เตรียม localStream
=======
// เตรียม localStream แต่ไม่เปิด track
>>>>>>> a5d1bc9f89d7de9335090e1327c095d68c2013a6
// ---------------------
async function initLocalStream() {
    if (localStream) return;
    try {
<<<<<<< HEAD
        localStream = await navigator.mediaDevices.getUserMedia({ 
            video: { width: 1280, height: 720 }, 
            audio: true 
        });
        localVideo.srcObject = localStream;

        // เริ่มต้นปิดทั้งกล้องและไมค์
        localStream.getAudioTracks()[0].enabled = true;
        localStream.getVideoTracks()[0].enabled = true;
        
        updateMicIcon();
        updateVideoIcon();
        
        console.log('[INFO] Local stream initialized');
    } catch (err) {
        console.error('[ERROR] Cannot access camera/microphone:', err);
        showMessage('ไม่สามารถเข้าถึงกล้องหรือไมโครโฟนได้', 'error');
=======
        localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        localVideo.srcObject = localStream;

        // เริ่มต้นปิดทั้งกล้องและไมค์
        localStream.getAudioTracks()[0].enabled = false;
        localStream.getVideoTracks()[0].enabled = false;

        updateMicIcon();
        updateVideoIcon();
    } catch (err) {
        console.error(err);
        alert('ไม่สามารถเข้าถึงกล้องหรือไมโครโฟนได้');
>>>>>>> a5d1bc9f89d7de9335090e1327c095d68c2013a6
    }
}

// ---------------------
// Toggle Mic / Video
// ---------------------
function toggleMic() {
<<<<<<< HEAD
    if (!localStream) {
        showMessage('กรุณาเปิดกล้องก่อน', 'warning');
        return;
    }
=======
    if (!localStream) return;
>>>>>>> a5d1bc9f89d7de9335090e1327c095d68c2013a6
    const track = localStream.getAudioTracks()[0];
    track.enabled = !track.enabled;
    updateMicIcon();
}

function toggleVideo() {
<<<<<<< HEAD
    if (!localStream) {
        showMessage('กรุณาเปิดกล้องก่อน', 'warning');
        return;
    }
=======
    if (!localStream) return;
>>>>>>> a5d1bc9f89d7de9335090e1327c095d68c2013a6
    const track = localStream.getVideoTracks()[0];
    track.enabled = !track.enabled;
    updateVideoIcon();
}

function updateMicIcon() {
    const icon = document.getElementById('micIcon');
<<<<<<< HEAD
    const isEnabled = localStream.getAudioTracks()[0].enabled;
    icon.className = isEnabled ? 'fas fa-microphone' : 'fas fa-microphone-slash';
    micBtn.classList.toggle('active', isEnabled);
=======
    icon.classList.toggle('fa-microphone-slash', !localStream.getAudioTracks()[0].enabled);
    icon.classList.toggle('fa-microphone', localStream.getAudioTracks()[0].enabled);
>>>>>>> a5d1bc9f89d7de9335090e1327c095d68c2013a6
}

function updateVideoIcon() {
    const icon = document.getElementById('videoIcon');
<<<<<<< HEAD
    const isEnabled = localStream.getVideoTracks()[0].enabled;
    icon.className = isEnabled ? 'fas fa-video' : 'fas fa-video-slash';
    videoBtn.classList.toggle('active', isEnabled);
}

// ---------------------
// เริ่มโทร (Doctor Calls Patient)
// ---------------------
async function toggleCall() {
    if (isCallActive) {
        endCall();
=======
    icon.classList.toggle('fa-video-slash', !localStream.getVideoTracks()[0].enabled);
    icon.classList.toggle('fa-video', localStream.getVideoTracks()[0].enabled);
}

// ---------------------
// โทร
// ---------------------
async function startCall() {
    if (!localStream) {
        alert('กรุณาเปิดกล้องหรือไมค์ก่อนโทร (สามารถเปิดได้ด้วยปุ่ม Mic/Video)');
>>>>>>> a5d1bc9f89d7de9335090e1327c095d68c2013a6
        return;
    }

    const hn = hnInput.value.trim();
    if (!hn) {
<<<<<<< HEAD
        showMessage('กรุณากรอก HN ของผู้ป่วย', 'warning');
        hnInput.focus();
        return;
    }

    // ตรวจสอบว่ามี HN นี้ในระบบหรือไม่
    try {
        const response = await fetch(`/api/check_patient/${hn}`);
        const data = await response.json();
        
        if (!data.success) {
            showMessage('ไม่พบผู้ป่วย HN: ' + hn, 'error');
            return;
        }
        
        // อัปเดตชื่อในฟอร์ม
        if (nameInput.value.trim() === '') {
            nameInput.value = data.name;
        }
        
    } catch (err) {
        console.error('[ERROR] Check patient failed:', err);
        showMessage('เกิดข้อผิดพลาดในการตรวจสอบข้อมูล', 'error');
        return;
    }

    if (!localStream) {
        await initLocalStream();
    }

    startCall(hn);
}

async function startCall(hn) {
    try {
        currentRoom = 'consultation_room_' + hn;
        
        // สร้าง peer connection
        peerConnection = new RTCPeerConnection(config);
        
        // เพิ่ม local tracks
        localStream.getTracks().forEach(track => {
            peerConnection.addTrack(track, localStream);
        });

        // รับ remote tracks
        peerConnection.ontrack = event => {
            console.log('[INFO] Remote track received');
            remoteVideo.srcObject = event.streams[0];
            updateStatus('เชื่อมต่อสำเร็จ', 'connected');
        };

        // จัดการ ICE candidates
        peerConnection.onicecandidate = event => {
            if (event.candidate) {
                console.log('[INFO] Sending ICE candidate');
                socket.emit('ice_candidate', { 
                    candidate: event.candidate, 
                    room: currentRoom 
                });
            }
        };

        // ตรวจสอบสถานะการเชื่อมต่อ
        peerConnection.oniceconnectionstatechange = () => {
            console.log('[INFO] ICE state:', peerConnection.iceConnectionState);
            if (peerConnection.iceConnectionState === 'disconnected' || 
                peerConnection.iceConnectionState === 'failed') {
                updateStatus('การเชื่อมต่อขาดหาย', 'disconnected');
            }
        };

        // Join room
        socket.emit('join', { room: currentRoom, username: 'Doctor' });

        // สร้างและส่ง offer
        const offer = await peerConnection.createOffer();
        await peerConnection.setLocalDescription(offer);
        
        console.log('[INFO] Sending offer');
        socket.emit('offer', { 
            sdp: offer.sdp, 
            type: offer.type, 
            room: currentRoom 
        });

        isCallActive = true;
        updateCallButton();
        updateStatus('กำลังโทรหาผู้ป่วย...', 'calling');
        
    } catch (err) {
        console.error('[ERROR] Start call failed:', err);
        showMessage('ไม่สามารถเริ่มการโทรได้', 'error');
        endCall();
    }
=======
        alert('กรุณากรอก HN ของผู้ป่วย');
        return;
    }

    peerConnection = new RTCPeerConnection(config);
    localStream.getTracks().forEach(track => peerConnection.addTrack(track, localStream));

    peerConnection.ontrack = event => {
        remoteVideo.srcObject = event.streams[0];
    };

    peerConnection.onicecandidate = event => {
        if (event.candidate) {
            const room = 'consultation_room_' + hn;
            socket.emit('ice_candidate', { candidate: event.candidate, room });
        }
    };

    const room = 'consultation_room_' + hn;
    socket.emit('join', { room, username: 'Doctor' });

    const offer = await peerConnection.createOffer();
    await peerConnection.setLocalDescription(offer);
    socket.emit('offer', { sdp: offer.sdp, type: offer.type, room });

    isCallActive = true;
>>>>>>> a5d1bc9f89d7de9335090e1327c095d68c2013a6
}

// ---------------------
// จบ Call
// ---------------------
function endCall() {
<<<<<<< HEAD
    console.log('[INFO] Ending call');
    
    if (peerConnection) {
        peerConnection.close();
        peerConnection = null;
    }

    if (remoteVideo.srcObject) {
        remoteVideo.srcObject.getTracks().forEach(track => track.stop());
        remoteVideo.srcObject = null;
    }

    if (currentRoom) {
        socket.emit('leave', { room: currentRoom, username: 'Doctor' });
        currentRoom = null;
    }

    isCallActive = false;
    updateCallButton();
    updateStatus('ไม่ได้เชื่อมต่อ', 'disconnected');
    showMessage('สิ้นสุดการโทร', 'info');
=======
    if (peerConnection) peerConnection.close();
    if (localStream) localStream.getTracks().forEach(track => track.stop());

    localVideo.srcObject = null;
    remoteVideo.srcObject = null;
    isCallActive = false;
    const room = 'consultation_room_' + hnInput.value.trim();
    socket.emit('leave', { room });
>>>>>>> a5d1bc9f89d7de9335090e1327c095d68c2013a6
}

// ---------------------
// Socket Events
// ---------------------
socket.on('answer_received', async data => {
<<<<<<< HEAD
    console.log('[INFO] Answer received');
    try {
        if (peerConnection) {
            await peerConnection.setRemoteDescription(
                new RTCSessionDescription({ sdp: data.sdp, type: data.type })
            );
            updateStatus('กำลังเชื่อมต่อ...', 'connecting');
        }
    } catch (err) {
        console.error('[ERROR] Set remote description failed:', err);
=======
    if (peerConnection) {
        await peerConnection.setRemoteDescription(new RTCSessionDescription({ sdp: data.sdp, type: data.type }));
>>>>>>> a5d1bc9f89d7de9335090e1327c095d68c2013a6
    }
});

socket.on('ice_candidate_received', data => {
<<<<<<< HEAD
    console.log('[INFO] ICE candidate received');
    if (peerConnection) {
        peerConnection.addIceCandidate(new RTCIceCandidate(data.candidate))
            .catch(err => console.error('[ERROR] Add ICE candidate failed:', err));
    }
});

socket.on('user_joined', data => {
    console.log('[INFO] User joined:', data.username);
    if (data.username === 'Patient') {
        showMessage('ผู้ป่วยเข้าร่วมแล้ว', 'success');
    }
});

socket.on('user_left', data => {
    console.log('[INFO] User left:', data.username);
    showMessage('ผู้ป่วยออกจากการโทร', 'warning');
    endCall();
});

// ---------------------
// UI Updates
// ---------------------
function updateCallButton() {
    const icon = document.getElementById('callIcon');
    if (isCallActive) {
        callBtn.classList.add('active');
        icon.className = 'fas fa-phone-slash';
        callBtn.title = 'วางสาย';
    } else {
        callBtn.classList.remove('active');
        icon.className = 'fas fa-phone';
        callBtn.title = 'โทรหาผู้ป่วย';
    }
}

function updateStatus(text, status) {
    statusText.textContent = text;
    statusDot.className = 'status-dot';
    if (status === 'connected') {
        statusDot.classList.add('connected');
    } else if (status === 'calling' || status === 'connecting') {
        statusDot.classList.add('calling');
    }
}

function showMessage(message, type = 'info') {
    const container = document.getElementById('messageContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    messageDiv.innerHTML = `
        <i class="fas fa-${type === 'error' ? 'exclamation-circle' : type === 'success' ? 'check-circle' : 'info-circle'}"></i>
        <span>${message}</span>
    `;
    container.appendChild(messageDiv);
    
    setTimeout(() => {
        messageDiv.classList.add('fade-out');
        setTimeout(() => messageDiv.remove(), 300);
    }, 3000);
}

// ---------------------
// Form Handling
// ---------------------
patientForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = {
        name: nameInput.value.trim(),
        HN: hnInput.value.trim(),
        notes: document.getElementById('notes').value.trim(),
        followUpDate: document.getElementById('followUpDate').value
    };

    if (!formData.name || !formData.HN) {
        showMessage('กรุณากรอกชื่อและ HN', 'warning');
        return;
    }

    try {
        const response = await fetch('/api/save_patient', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });

        const result = await response.json();
        
        if (result.success) {
            showMessage('บันทึกข้อมูลสำเร็จ', 'success');
            document.getElementById('updateTime').textContent = result.updated_at;
        } else {
            showMessage('เกิดข้อผิดพลาด: ' + result.error, 'error');
        }
    } catch (err) {
        console.error('[ERROR] Save patient failed:', err);
        showMessage('ไม่สามารถบันทึกข้อมูลได้', 'error');
    }
});

function clearForm() {
    if (confirm('ต้องการล้างข้อมูลหรือไม่?')) {
        document.getElementById('notes').value = '';
        document.getElementById('followUpDate').value = '';
        showMessage('ล้างข้อมูลแล้ว', 'info');
    }
}

// ---------------------
// Initialize
// ---------------------
window.addEventListener('load', () => {
    initLocalStream();
    updateCallButton();
    updateStatus('ไม่ได้เชื่อมต่อ', 'disconnected');
});

// ป้องกันการปิดหน้าต่างขณะโทร
window.addEventListener('beforeunload', (e) => {
    if (isCallActive) {
        e.preventDefault();
        e.returnValue = '';
    }
});
=======
    if (peerConnection) peerConnection.addIceCandidate(new RTCIceCandidate(data.candidate));
});

socket.on('user_joined', data => {
    statusText.textContent = `${data.username} เข้าร่วม`;
    statusDot.classList.add('connected');
});

// ---------------------
// Event Listeners
// ---------------------
window.addEventListener('load', initLocalStream);
micBtn.onclick = toggleMic;
videoBtn.onclick = toggleVideo;
callBtn.onclick = startCall;
endCallBtn.onclick = endCall;
>>>>>>> a5d1bc9f89d7de9335090e1327c095d68c2013a6
