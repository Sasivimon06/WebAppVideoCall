// ------------------ Socket.io ------------------
const socket = io();

// ------------------ Global Variables ------------------
let localStream;
let peerConnection;
let isCallActive = false;

// Video elements
const localVideo = document.getElementById('patientVideo');
const remoteVideo = document.getElementById('hostVideo'); // หมอเป็น Host

// Status elements
const statusText = document.getElementById('statusText');
const statusDot = document.getElementById('statusDot');

// ดึง HN จาก HTML (session/last_patient)
const currentHN = document.getElementById('currentHN').textContent.split(': ')[1];
console.log("Current patient HN:", currentHN);

// ------------------ ICE Servers ------------------
const config = {
    iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'turn:openrelay.metered.ca:80', username: 'openrelay', credential: 'openrelay' }
    ]
};

// ------------------ Start Local Video ------------------
async function startLocalVideo() {
    try {
        localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        localVideo.srcObject = localStream;

        // เริ่มปิดไมค์และวิดีโอ
        localStream.getAudioTracks()[0].enabled = false;
        localStream.getVideoTracks()[0].enabled = false;

        peerConnection = new RTCPeerConnection(config);
        localStream.getTracks().forEach(track => peerConnection.addTrack(track, localStream));

        peerConnection.ontrack = event => {
            remoteVideo.srcObject = event.streams[0];
        };

        peerConnection.onicecandidate = event => {
            if (event.candidate) {
                socket.emit('ice_candidate', { candidate: event.candidate, room: getRoomName() });
            }
        };

    } catch (err) {
        console.error('Error accessing media devices:', err);
        alert('ไม่สามารถเข้าถึงกล้องหรือไมโครโฟนได้');
    }
}

// ------------------ Answer Call ------------------
async function answerCall() {
    if (isCallActive) return;
    await startLocalVideo();

    const room = getRoomName();
    socket.emit('join', { room: room, username: 'Patient' });

    isCallActive = true;
    document.getElementById('answerBtn').disabled = true;
}

// ------------------ Toggle Mic ------------------
function toggleMic() {
    if (!localStream) return;
    const track = localStream.getAudioTracks()[0];
    track.enabled = !track.enabled;
    document.getElementById('micIcon').classList.toggle('fa-microphone-slash');
}

// ------------------ Toggle Video ------------------
function toggleVideo() {
    if (!localStream) return;
    const track = localStream.getVideoTracks()[0];
    track.enabled = !track.enabled;
    document.getElementById('videoIcon').classList.toggle('fa-video-slash');
}

// ------------------ End Call ------------------
function endCall() {
    const room = getRoomName();
    if (peerConnection) peerConnection.close();
    if (localStream) localStream.getTracks().forEach(track => track.stop());
    localVideo.srcObject = null;
    remoteVideo.srcObject = null;
    isCallActive = false;
    socket.emit('leave', { room: room });
    document.getElementById('answerBtn').disabled = false;
}

// ------------------ Helper: Room Name ------------------
function getRoomName() {
    return 'consultation_room_' + currentHN;
}

// ------------------ Socket Events ------------------
socket.on('offer_received', async data => {
    await peerConnection.setRemoteDescription(new RTCSessionDescription({ sdp: data.sdp, type: data.type }));
    const answer = await peerConnection.createAnswer();
    await peerConnection.setLocalDescription(answer);
    socket.emit('answer', { sdp: answer.sdp, type: answer.type, room: getRoomName() });
});

socket.on('ice_candidate_received', data => {
    peerConnection.addIceCandidate(new RTCIceCandidate(data.candidate));
});

socket.on('user_joined', data => {
    statusText.textContent = `${data.username} เข้าร่วม`;
    statusDot.classList.add('connected');
});
