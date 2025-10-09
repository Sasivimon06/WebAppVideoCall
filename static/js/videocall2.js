// static/js/videocall2.js

const socket = io(); // connect to server
let localStream = null;
let peerConnection = null;

const servers = {
    iceServers: [
        { urls: "stun:stun.l.google.com:19302" } // free STUN server
    ]
};

const localVideo = document.getElementById("localVideo");
const remoteVideo = document.getElementById("remoteVideo");
const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const micIcon = document.getElementById("micIcon");
const videoIcon = document.getElementById("videoIcon");
const callIcon = document.getElementById("callIcon");

let isMicOn = true;
let isVideoOn = true;
let isInCall = false;

/* ----------------- Video/Audio Setup ----------------- */
async function startMedia() {
    try {
        localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        localVideo.srcObject = localStream;
    } catch (err) {
        console.error("ไม่สามารถเข้าถึงกล้อง/ไมค์:", err);
    }
}

/* ----------------- Call Controls ----------------- */
function toggleMic() {
    if (!localStream) return;
    isMicOn = !isMicOn;
    localStream.getAudioTracks().forEach(track => track.enabled = isMicOn);
    micIcon.className = isMicOn ? "fas fa-microphone" : "fas fa-microphone-slash";
}

function toggleVideo() {
    if (!localStream) return;
    isVideoOn = !isVideoOn;
    localStream.getVideoTracks().forEach(track => track.enabled = isVideoOn);
    videoIcon.className = isVideoOn ? "fas fa-video" : "fas fa-video-slash";
}

function toggleCall() {
    if (!isInCall) {
        startCall();
    } else {
        endCall();
    }
}

function endCall() {
    if (peerConnection) {
        peerConnection.close();
        peerConnection = null;
    }
    remoteVideo.srcObject = null;
    isInCall = false;
    callIcon.className = "fas fa-phone";
    updateStatus(false, "Call Ended");
    socket.emit("leave");
}

/* ----------------- WebRTC Call Setup ----------------- */
async function startCall() {
    await startMedia();

    peerConnection = new RTCPeerConnection(servers);

    // Add local stream
    localStream.getTracks().forEach(track => peerConnection.addTrack(track, localStream));

    // Remote stream
    peerConnection.ontrack = (event) => {
        remoteVideo.srcObject = event.streams[0];
    };

    // ICE candidates
    peerConnection.onicecandidate = (event) => {
        if (event.candidate) {
            socket.emit("ice-candidate", event.candidate);
        }
    };

    // Create and send offer
    const offer = await peerConnection.createOffer();
    await peerConnection.setLocalDescription(offer);
    socket.emit("offer", offer);

    isInCall = true;
    callIcon.className = "fas fa-phone-slash";
    updateStatus(true, "Connected");
}

/* ----------------- Socket.IO Handlers ----------------- */
socket.on("offer", async (offer) => {
    if (!peerConnection) {
        await startMedia();
        peerConnection = new RTCPeerConnection(servers);

        localStream.getTracks().forEach(track => peerConnection.addTrack(track, localStream));

        peerConnection.ontrack = (event) => {
            remoteVideo.srcObject = event.streams[0];
        };

        peerConnection.onicecandidate = (event) => {
            if (event.candidate) {
                socket.emit("ice-candidate", event.candidate);
            }
        };
    }

    await peerConnection.setRemoteDescription(new RTCSessionDescription(offer));
    const answer = await peerConnection.createAnswer();
    await peerConnection.setLocalDescription(answer);
    socket.emit("answer", answer);

    isInCall = true;
    callIcon.className = "fas fa-phone-slash";
    updateStatus(true, "Connected");
});

socket.on("answer", async (answer) => {
    if (peerConnection) {
        await peerConnection.setRemoteDescription(new RTCSessionDescription(answer));
    }
});

socket.on("ice-candidate", async (candidate) => {
    if (peerConnection) {
        try {
            await peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
        } catch (err) {
            console.error("Error adding received ICE candidate", err);
        }
    }
});

socket.on("leave", () => {
    endCall();
});

/* ----------------- UI Helpers ----------------- */
function updateStatus(connected, text) {
    statusDot.style.backgroundColor = connected ? "green" : "red";
    statusText.innerText = text;
}

// Auto start camera/mic preview
startMedia();
