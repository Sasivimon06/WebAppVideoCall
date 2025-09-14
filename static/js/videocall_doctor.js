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

const socket = io();
let localStream = null;
let peerConnection = null;
let isCallActive = false;

// ICE Config
const config = {
    iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'turn:openrelay.metered.ca:80', username: 'openrelay', credential: 'openrelay' }
    ]
};

// ---------------------
// เตรียม localStream แต่ไม่เปิด track
// ---------------------
async function initLocalStream() {
    if (localStream) return;
    try {
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
    }
}

// ---------------------
// Toggle Mic / Video
// ---------------------
function toggleMic() {
    if (!localStream) return;
    const track = localStream.getAudioTracks()[0];
    track.enabled = !track.enabled;
    updateMicIcon();
}

function toggleVideo() {
    if (!localStream) return;
    const track = localStream.getVideoTracks()[0];
    track.enabled = !track.enabled;
    updateVideoIcon();
}

function updateMicIcon() {
    const icon = document.getElementById('micIcon');
    icon.classList.toggle('fa-microphone-slash', !localStream.getAudioTracks()[0].enabled);
    icon.classList.toggle('fa-microphone', localStream.getAudioTracks()[0].enabled);
}

function updateVideoIcon() {
    const icon = document.getElementById('videoIcon');
    icon.classList.toggle('fa-video-slash', !localStream.getVideoTracks()[0].enabled);
    icon.classList.toggle('fa-video', localStream.getVideoTracks()[0].enabled);
}

// ---------------------
// โทร
// ---------------------
async function startCall() {
    if (!localStream) {
        alert('กรุณาเปิดกล้องหรือไมค์ก่อนโทร (สามารถเปิดได้ด้วยปุ่ม Mic/Video)');
        return;
    }

    const hn = hnInput.value.trim();
    if (!hn) {
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
}

// ---------------------
// จบ Call
// ---------------------
function endCall() {
    if (peerConnection) peerConnection.close();
    if (localStream) localStream.getTracks().forEach(track => track.stop());

    localVideo.srcObject = null;
    remoteVideo.srcObject = null;
    isCallActive = false;
    const room = 'consultation_room_' + hnInput.value.trim();
    socket.emit('leave', { room });
}

// ---------------------
// Socket Events
// ---------------------
socket.on('answer_received', async data => {
    if (peerConnection) {
        await peerConnection.setRemoteDescription(new RTCSessionDescription({ sdp: data.sdp, type: data.type }));
    }
});

socket.on('ice_candidate_received', data => {
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
