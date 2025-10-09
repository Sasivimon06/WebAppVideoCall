// -----------------------------
// Client-side Video Call Script
// -----------------------------
const localVideo = document.getElementById("localVideo");
const remoteVideo = document.getElementById("remoteVideo");

const room = prompt("Enter room name to join:") || "testRoom";  // ให้ผู้ใช้กรอกห้อง
const username = "user_" + Math.floor(Math.random() * 1000);

let localStream;
let peerConnection;
const config = {
    iceServers: [
        { urls: "stun:stun.l.google.com:19302" } // ใช้ Google STUN
    ]
};

// เชื่อมต่อไปยัง Socket.IO server
const socket = io();

// -----------------------------
// เตรียมกล้อง/ไมค์
// -----------------------------
async function initLocalStream() {
    try {
        localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        localVideo.srcObject = localStream;
    } catch (err) {
        console.error("ไม่สามารถเข้าถึงกล้อง/ไมค์:", err);
    }
}

// -----------------------------
// สร้าง PeerConnection
// -----------------------------
function createPeerConnection() {
    peerConnection = new RTCPeerConnection(config);

    // ส่ง local tracks เข้า peer connection
    localStream.getTracks().forEach(track => peerConnection.addTrack(track, localStream));

    // แสดง remote stream
    peerConnection.ontrack = event => {
        remoteVideo.srcObject = event.streams[0];
    };

    // ส่ง ICE candidate ไป server
    peerConnection.onicecandidate = event => {
        if (event.candidate) {
            socket.emit("candidate", {
                room,
                candidate: event.candidate,
                user: username
            });
        }
    };
}

// -----------------------------
// Socket.IO Events
// -----------------------------
socket.on("connect", () => {
    console.log("เชื่อมต่อกับ signaling server แล้ว");
    socket.emit("join", { room, user: username });
});

socket.on("user-joined", data => {
    console.log("มีผู้ใช้ใหม่เข้าห้อง:", data);

    // เราเป็นฝ่าย Caller → สร้าง offer
    createPeerConnection();
    peerConnection.createOffer()
        .then(offer => {
            peerConnection.setLocalDescription(offer);
            socket.emit("offer", { room, offer, user: username });
        });
});

socket.on("offer", data => {
    console.log("ได้รับ offer:", data);
    createPeerConnection();
    peerConnection.setRemoteDescription(new RTCSessionDescription(data.offer));

    peerConnection.createAnswer()
        .then(answer => {
            peerConnection.setLocalDescription(answer);
            socket.emit("answer", { room, answer, user: username });
        });
});

socket.on("answer", data => {
    console.log("ได้รับ answer:", data);
    peerConnection.setRemoteDescription(new RTCSessionDescription(data.answer));
});

socket.on("candidate", data => {
    console.log("ได้รับ candidate:", data);
    peerConnection.addIceCandidate(new RTCIceCandidate(data.candidate));
});

socket.on("user-left", data => {
    console.log("คู่สนทนาออกจากห้อง:", data);
    if (remoteVideo.srcObject) {
        remoteVideo.srcObject.getTracks().forEach(track => track.stop());
    }
    remoteVideo.srcObject = null;
});

// -----------------------------
// เริ่มต้นใช้งาน
// -----------------------------
initLocalStream();
