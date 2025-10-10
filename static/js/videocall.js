const localVideo = document.getElementById("localVideo");
const remoteVideo = document.getElementById("remoteVideo");

// ดึง HN จาก element ที่มี id="currentHN"
const hnElement = document.getElementById("currentHN");
const room = hnElement ? hnElement.textContent.replace("HN: ", "").trim() : "testRoom";
console.log("Joining room:", room);

const username = document.querySelector(".patient-details h3") ? 
                document.querySelector(".patient-details h3").textContent : 
                "user_" + Math.floor(Math.random() * 1000);

let localStream;
let peerConnection;
const config = { iceServers: [{ urls: "stun:stun.l.google.com:19302" }] };

const socket = io();

// -----------------------------
// เตรียมกล้อง/ไมค์
// -----------------------------
async function initLocalStream() {
    localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
    localVideo.srcObject = localStream;
}

// -----------------------------
// สร้าง PeerConnection
// -----------------------------
function createPeerConnection() {
    peerConnection = new RTCPeerConnection(config);

    // ส่ง local tracks
    localStream.getTracks().forEach(track => peerConnection.addTrack(track, localStream));

    // แสดง remote stream
    peerConnection.ontrack = event => {
        remoteVideo.srcObject = event.streams[0];
    };

    // ส่ง ICE candidate
    peerConnection.onicecandidate = event => {
        if (event.candidate) {
            socket.emit("candidate", { room, candidate: event.candidate });
        }
    };
}

// -----------------------------
// Socket.IO Events
// -----------------------------
socket.on("connect", () => {
    console.log("เชื่อมต่อ signaling server");
    socket.emit("join", { room, user: username });
});

// ใครเข้าห้องแล้ว notify
socket.on("user-joined", data => {
    console.log("มีผู้ใช้เข้าห้อง:", data);

    // ถ้าเราเป็นคนแรก → เป็น Caller
    if (!peerConnection) {
        createPeerConnection();
        peerConnection.createOffer().then(offer => {
            peerConnection.setLocalDescription(offer);
            socket.emit("offer", { room, offer });
        });
    }
});

// รับ offer → ตอบ answer
socket.on("offer", data => {
    console.log("ได้รับ offer:", data);
    if (!peerConnection) createPeerConnection();

    peerConnection.setRemoteDescription(new RTCSessionDescription(data.offer))
        .then(() => peerConnection.createAnswer())
        .then(answer => {
            peerConnection.setLocalDescription(answer);
            socket.emit("answer", { room, answer });
        });
});

// รับ answer
socket.on("answer", data => {
    console.log("ได้รับ answer:", data);
    peerConnection.setRemoteDescription(new RTCSessionDescription(data.answer));
});

// รับ ICE candidate
socket.on("candidate", data => {
    console.log("ได้รับ candidate:", data);
    if (peerConnection) peerConnection.addIceCandidate(new RTCIceCandidate(data.candidate));
});

// ใครออกห้อง
socket.on("user-left", data => {
    console.log("คู่สนทนาออกจากห้อง:", data);
    if (remoteVideo.srcObject) {
        remoteVideo.srcObject.getTracks().forEach(track => track.stop());
    }
    remoteVideo.srcObject = null;
});

// -----------------------------
// เริ่มใช้งาน
// -----------------------------
initLocalStream();
