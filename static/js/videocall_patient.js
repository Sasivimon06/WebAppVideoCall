// ------------------ Socket.io ------------------
const socket = io();

// ------------------ Global Variables ------------------
let localStream;
let peerConnection;
let isCallActive = false;
let currentRoom = null;

// Video elements
const localVideo = document.getElementById('patientVideo');
const remoteVideo = document.getElementById('hostVideo');

// Status elements
const statusText = document.getElementById('statusText');
const statusDot = document.getElementById('statusDot');

// Control buttons
const answerBtn = document.getElementById('answerBtn');
const endCallBtn = document.getElementById('endCallBtn');
const micBtn = document.getElementById('micBtn');
const videoBtn = document.getElementById('videoBtn');

// ดึง HN จาก template (ส่งมาจาก Flask)
const patientData = window.patientData || {};
const currentHN = patientData.HN;

console.log('[INFO] Patient HN:', currentHN);

// ------------------ ICE Servers ------------------
const config = {
    iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' },
        { urls: 'turn:openrelay.metered.ca:80', username: 'openrelay', credential: 'openrelay' }
    ]
};

// ------------------ Start Local Video ------------------
async function startLocalVideo() {
    if (localStream) return;
    
    try {
        localStream = await navigator.mediaDevices.getUserMedia({ 
            video: { width: 1280, height: 720 }, 
            audio: true 
        });
        localVideo.srcObject = localStream;

        // เริ่มเปิดกล้องและไมค์ (เพื่อให้เห็นตัวเอง)
        localStream.getAudioTracks()[0].enabled = true;
        localStream.getVideoTracks()[0].enabled = true;
        
        updateMicIcon();
        updateVideoIcon();

        console.log('[INFO] Local video started');
    } catch (err) {
        console.error('[ERROR] Cannot access media devices:', err);
        showMessage('ไม่สามารถเข้าถึงกล้องหรือไมโครโฟนได้', 'error');
    }
}

// ------------------ Setup Peer Connection ------------------
function setupPeerConnection() {
    peerConnection = new RTCPeerConnection(config);

    // เพิ่ม local tracks
    if (localStream) {
        localStream.getTracks().forEach(track => {
            peerConnection.addTrack(track, localStream);
        });
    }

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
                room: getRoomName() 
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
}

// ------------------ Answer Call ------------------
async function answerCall() {
    if (isCallActive) return;

    console.log('[INFO] Answering call');
    
    await startLocalVideo();
    setupPeerConnection();

    currentRoom = getRoomName();
    socket.emit('join', { room: currentRoom, username: 'Patient' });

    isCallActive = true;
    answerBtn.disabled = true;
    answerBtn.style.display = 'none';
    endCallBtn.style.display = 'inline-flex';
    
    updateStatus('รอการเชื่อมต่อ...', 'connecting');
    showMessage('กำลังเชื่อมต่อกับแพทย์...', 'info');
}

// ------------------ Toggle Mic ------------------
function toggleMic() {
    if (!localStream) {
        showMessage('กรุณารับสายก่อน', 'warning');
        return;
    }
    const track = localStream.getAudioTracks()[0];
    track.enabled = !track.enabled;
    updateMicIcon();
}

function updateMicIcon() {
    const icon = document.getElementById('micIcon');
    const isEnabled = localStream.getAudioTracks()[0].enabled;
    icon.className = isEnabled ? 'fas fa-microphone' : 'fas fa-microphone-slash';
    micBtn.classList.toggle('active', isEnabled);
}

// ------------------ Toggle Video ------------------
function toggleVideo() {
    if (!localStream) {
        showMessage('กรุณารับสายก่อน', 'warning');
        return;
    }
    const track = localStream.getVideoTracks()[0];
    track.enabled = !track.enabled;
    updateVideoIcon();
}

function updateVideoIcon() {
    const icon = document.getElementById('videoIcon');
    const isEnabled = localStream.getVideoTracks()[0].enabled;
    icon.className = isEnabled ? 'fas fa-video' : 'fas fa-video-slash';
    videoBtn.classList.toggle('active', isEnabled);
}

// ------------------ End Call ------------------
function endCall() {
    console.log('[INFO] Ending call');

    if (peerConnection) {
        peerConnection.close();
        peerConnection = null;
    }

    if (localStream) {
        localStream.getTracks().forEach(track => track.stop());
        localStream = null;
    }

    if (remoteVideo.srcObject) {
        remoteVideo.srcObject.getTracks().forEach(track => track.stop());
        remoteVideo.srcObject = null;
    }

    localVideo.srcObject = null;

    if (currentRoom) {
        socket.emit('leave', { room: currentRoom, username: 'Patient' });
        currentRoom = null;
    }

    isCallActive = false;
    answerBtn.disabled = false;
    answerBtn.style.display = 'inline-flex';
    endCallBtn.style.display = 'none';
    
    updateStatus('ยังไม่ได้รับสาย', 'disconnected');
    showMessage('สิ้นสุดการโทร', 'info');
}

// ------------------ Helper: Room Name ------------------
function getRoomName() {
    // ใช้ HN เป็น room name (ต้องตรงกับฝั่งหมอ)
    return 'consultation_room_' + currentHN;
}

// ------------------ Socket Events ------------------
socket.on('offer_received', async data => {
    console.log('[INFO] Offer received');
    
    if (!isCallActive) {
        // แสดงปุ่มรับสาย
        answerBtn.classList.add('ringing');
        showMessage('มีสายเรียกเข้าจากแพทย์!', 'success');
        updateStatus('มีสายเรียกเข้า...', 'ringing');
        
        // เล่นเสียงเรียกเข้า (optional)
        playRingtone();
    }
    
    try {
        if (peerConnection) {
            await peerConnection.setRemoteDescription(
                new RTCSessionDescription({ sdp: data.sdp, type: data.type })
            );
            
            const answer = await peerConnection.createAnswer();
            await peerConnection.setLocalDescription(answer);
            
            console.log('[INFO] Sending answer');
            socket.emit('answer', { 
                sdp: answer.sdp, 
                type: answer.type, 
                room: getRoomName() 
            });
            
            updateStatus('กำลังเชื่อมต่อ...', 'connecting');
        }
    } catch (err) {
        console.error('[ERROR] Handle offer failed:', err);
        showMessage('เกิดข้อผิดพลาดในการรับสาย', 'error');
    }
});

socket.on('ice_candidate_received', data => {
    console.log('[INFO] ICE candidate received');
    if (peerConnection) {
        peerConnection.addIceCandidate(new RTCIceCandidate(data.candidate))
            .catch(err => console.error('[ERROR] Add ICE candidate failed:', err));
    }
});

socket.on('user_joined', data => {
    console.log('[INFO] User joined:', data.username);
    if (data.username === 'Doctor') {
        showMessage('แพทย์เข้าร่วมแล้ว', 'success');
    }
});

socket.on('user_left', data => {
    console.log('[INFO] User left:', data.username);
    showMessage('แพทย์ออกจากการโทร', 'warning');
    endCall();
});

// ------------------ UI Updates ------------------
function updateStatus(text, status) {
    statusText.textContent = text;
    statusDot.className = 'status-dot';
    if (status === 'connected') {
        statusDot.classList.add('connected');
    } else if (status === 'ringing' || status === 'connecting') {
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

// ------------------ Ringtone (Optional) ------------------
let ringtone = null;
function playRingtone() {
    // สามารถใส่ไฟล์เสียงเรียกเข้าได้
    // ringtone = new Audio('/static/sounds/ringtone.mp3');
    // ringtone.loop = true;
    // ringtone.play();
}

function stopRingtone() {
    if (ringtone) {
        ringtone.pause();
        ringtone = null;
    }
}

// ------------------ Initialize ------------------
window.addEventListener('load', () => {
    if (!currentHN) {
        showMessage('ไม่พบข้อมูลผู้ป่วย กรุณาลงทะเบียนก่อน', 'error');
        answerBtn.disabled = true;
        return;
    }

    // Join room และรอรับสาย
    currentRoom = getRoomName();
    socket.emit('join', { room: currentRoom, username: 'Patient_Waiting' });
    
    updateStatus('พร้อมรับสาย', 'ready');
    endCallBtn.style.display = 'none';
    
    console.log('[INFO] Patient ready in room:', currentRoom);
});

// ป้องกันการปิดหน้าต่างขณะโทร
window.addEventListener('beforeunload', (e) => {
    if (isCallActive) {
        e.preventDefault();
        e.returnValue = '';
    }
});