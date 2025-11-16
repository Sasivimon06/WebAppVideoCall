// สถานะการเรียน
const defaultProgress = {
    topic1: { pretest:false, learn:false, posttest:false },
    topic2: { pretest:false, learn:false, posttest:false },
    topic3: { pretest:false, learn:false, posttest:false }
};

// ข้อมูลหัวข้อ
const topics = {
    topic1: { title: 'การล้างมือ', description: 'เรียนรู้ความสำคัญของการล้างมือและวิธีการล้างมือที่ถูกต้อง' },
    topic2: { title: 'การนอนหลับ', description: 'เรียนรู้ความสำคัญของการนอนหลับและวิธีการนอนที่มีคุณภาพ' },
    topic3: { title: 'โภชนาการ', description: 'เรียนรู้หลักการโภชนาการและการรับประทานอาหารเพื่อสุขภาพ' }
};

// ตัวแปรสถานะปัจจุบัน
let currentTopic = localStorage.getItem('currentTopic') || '';
let currentStep = localStorage.getItem('currentStep') || '';
let progress = JSON.parse(JSON.stringify(defaultProgress));
let currentUser = document.body.dataset.currentUser || 'guest';
console.log('Current user:', currentUser);

// เริ่มต้น
document.addEventListener('DOMContentLoaded', async function() {
    initializeEventListeners();

    // ✅ รอให้โหลด progress เสร็จก่อน
    if(currentUser && currentUser !== 'guest'){
        await loadProgressFromPython();
    } else {
        loadProgress();
    }

    console.log('=== Progress after loading ===');
    console.log('Current user:', currentUser);
    console.log('Progress object:', JSON.stringify(progress, null, 2));
    console.log('============================');

    // ✅ ตอนนี้ progress พร้อมแล้ว
    restoreLastPage();
    
    // ✅ อัปเดต UI อีกครั้งเพื่อให้แน่ใจ
    updateProgressBars();
});

// ฟังก์ชันบันทึกหน้าเดิม
function restoreLastPage() {
    const savedPage = localStorage.getItem('currentPage');

    if (savedPage === 'home-page') {
        showHomePage();
    } else if (savedPage === 'topic-page' && currentTopic) {
        showTopicPage(currentTopic);  // progress ของ topic ถูกโหลดแล้ว
    } else if (savedPage === 'step-page' && currentTopic && currentStep) {
        showTopicPage(currentTopic);  // โหลด topic ก่อน
        showStepPage(currentStep);    // แล้วค่อยเปิด step
    } else {
        showHomePage();
    }
}

// เพิ่ม Event Listeners
function initializeEventListeners() {
    document.querySelectorAll('.topic-card').forEach(card => {
        card.addEventListener('click', function() {
            const topicId = this.getAttribute('data-topic');
            showTopicPage(topicId);
        });
    });

    document.querySelectorAll('.step-card').forEach(card => {
        card.addEventListener('click', function() {
            const stepId = this.getAttribute('data-step');
            showStepPage(stepId);
        });
    });
}

// แสดงหน้าหลัก
function showHomePage() {
    document.querySelectorAll('.page').forEach(page => page.classList.remove('active'));
    document.getElementById('home-page').classList.add('active');

    updateStepStatus(); // อัปเดต step card
    updateProgressBars(); // อัปเดต progress bar

    localStorage.setItem('currentPage', 'home-page');
    localStorage.removeItem('currentTopic');
    localStorage.removeItem('currentStep');
}

// แสดงหน้าหัวข้อ
function showTopicPage(topicId = currentTopic) {
    currentTopic = topicId;

    document.querySelectorAll('.page').forEach(page => page.classList.remove('active'));
    document.getElementById('topic-page').classList.add('active');

    document.getElementById('topic-title').textContent = topics[topicId].title;
    document.getElementById('topic-description').textContent = topics[topicId].description;

    updateStepStatus();
    updateProgressBars(); // <--- เพิ่มตรงนี้

    localStorage.setItem('currentPage', 'topic-page');
    localStorage.setItem('currentTopic', currentTopic);
    localStorage.removeItem('currentStep');
}

// แสดงหน้าขั้นตอน
function showStepPage(stepId) {
    currentStep = stepId;

    document.querySelectorAll('.page').forEach(page => page.classList.remove('active'));
    document.getElementById('step-page').classList.add('active');

    createStepContent(stepId);

    localStorage.setItem('currentPage', 'step-page');
    localStorage.setItem('currentTopic', currentTopic);
    localStorage.setItem('currentStep', currentStep);
}

// สร้างเนื้อหาขั้นตอน
function createStepContent(stepId) {
    const contentDiv = document.getElementById('step-content');
    const topicTitle = topics[currentTopic].title;

    let content = '';
    switch(stepId) {
        case 'pretest':
            content = `<div class="step-content">
                <h2>แบบทดสอบก่อนเรียน: ${topicTitle}</h2>
                <div class="question">
                    <p>คำถามที่ 1: ความรู้พื้นฐานเกี่ยวกับหัวข้อนี้คืออะไร?</p>
                    <div class="options">
                        <label><input type="radio" name="q1" value="a"> ตัวเลือก A</label>
                        <label><input type="radio" name="q1" value="b"> ตัวเลือก B</label>
                        <label><input type="radio" name="q1" value="c"> ตัวเลือก C</label>
                        <label><input type="radio" name="q1" value="d"> ตัวเลือก D</label>
                    </div>
                </div>
                <button class="btn-primary" onclick="completeStep('pretest')">ส่งคำตอบ</button>
            </div>`;
            break;
        case 'learn':
            content = `<div class="step-content">
                <h2>เริ่มเรียน: ${topicTitle}</h2>
                <div class="learning-content">
                    <h3>บทที่ 1: แนะนำ</h3>
                    <p>เนื้อหาการเรียนรู้สำหรับหัวข้อ "${topicTitle}" จะครอบคลุมแนวคิดพื้นฐานและการประยุกต์ใช้งานจริง</p>
                    
                    <h3>หัวข้อสำคัญ:</h3>
                    <ul>
                        <li>แนวคิดพื้นฐานและหลักการ</li>
                        <li>ตัวอย่างการใช้งานในชีวิตจริง</li>
                        <li>แนวทางการพัฒนาทักษะ</li>
                        <li>เทคนิคและเคล็ดลับ</li>
                    </ul>
                    
                    <div class="activity-box">
                        <h4>กิจกรรมฝึกหัด:</h4>
                        <p>ลองปฏิบัติตามตัวอย่างและทดสอบความเข้าใจ</p>
                    </div>
                    
                    <h3>สรุป</h3>
                    <p>การเรียนรู้หัวข้อนี้จะช่วยให้คุณมีพื้นฐานที่แข็งแกร่งสำหรับการพัฒนาต่อไป</p>
                </div>
                <button class="btn-primary" onclick="completeStep('learn')">เรียนจบ</button>
            </div>`;
            break;
        case 'posttest':
            content = `<div class="step-content">
                <h2>แบบทดสอบหลังเรียน: ${topicTitle}</h2>
                <div class="question">
                    <p>คำถามที่ 1: จากที่เรียนมา ให้อธิบายแนวคิดหลัก</p>
                    <textarea placeholder="พิมพ์คำตอบของคุณที่นี่..."></textarea>
                </div>
                <button class="btn-primary" onclick="completeStep('posttest')">ส่งคำตอบ</button>
            </div>`;
            break;
    }

    contentDiv.innerHTML = content;
}


// เสร็จสิ้นขั้นตอน
async function completeStep(stepId) {
    if(!currentUser || currentUser === 'guest'){
        alert('กรุณาล็อกอินก่อนทำแบบทดสอบ');
        return;
    }

    let score = 0;

    if(stepId === 'pretest' || stepId === 'posttest'){
        score = Math.floor(Math.random()*41)+60; // 60-100
    } else if(stepId === 'learn'){
        score = 100;
    }

    // ✅ อัพเดท progress local ก่อน
    progress[currentTopic][stepId] = true;

    // ✅ ส่งไป server แบบเดี่ยว (สำหรับแสดง score)
    try {
        const response = await fetch('/api/submit_answer', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({
                username: currentUser,
                topic_id: currentTopic,
                step_id: stepId,
                answers: {},
                score: score
            })
        });
        const result = await response.json();
        if(result.success){
            alert(`ส่งคำตอบสำเร็จ! คะแนน: ${score}`);
        } else {
            alert('เกิดข้อผิดพลาด: ' + result.error);
        }
    } catch(err){
        console.error(err);
        alert('ไม่สามารถส่งคำตอบไป server ได้');
    }

    // ✅ บันทึก progress ทั้งหมด
    await saveProgress();
    
    // ✅ อัปเดต UI
    showTopicPage(currentTopic);
}

// อัพเดทสถานะขั้นตอน
function updateStepStatus() {
    if(!currentTopic || !progress[currentTopic]) return;

    const stepCards = document.querySelectorAll('.step-card');
    const steps = ['pretest', 'learn', 'posttest'];

    stepCards.forEach((card, index) => {
        const stepId = steps[index];
        const button = card.querySelector('.btn-step');

        if (progress[currentTopic][stepId]) {
            card.classList.add('completed');
            button.textContent = 'เสร็จสมบูรณ์';
            button.classList.add('completed');
        } else {
            card.classList.remove('completed');
            button.textContent = 'เริ่มต้น';
            button.classList.remove('completed');
        }
    });
}

// อัพเดท Progress Bar
function updateProgressBars() {
    // ✅ ตรวจสอบว่า progress โหลดแล้วหรือยัง
    if (!progress || Object.keys(progress).length === 0) {
        console.log('Progress not loaded yet, skipping update');
        return;
    }

    document.querySelectorAll('.topic-card').forEach(card => {
        const topicId = card.dataset.topic;
        if (!progress[topicId]) {
            console.log(`No progress data for ${topicId}`);
            return;
        }

        const topicProgress = progress[topicId];

        // นับจำนวน step ที่เสร็จ
        const completed = Object.values(topicProgress).filter(v => v === true).length;
        const total = Object.keys(topicProgress).length;

        // อัปเดต progress bar และตัวเลข
        const progressBar = card.querySelector('.progress');
        const progressCount = card.querySelector('.progress-count');

        if (!progressBar) {
            console.log(`Progress bar not found for ${topicId}`);
            return;
        }

        const percentage = Math.round((completed / total) * 100);
        progressBar.style.width = percentage + '%';
        progressBar.setAttribute('data-progress', percentage);

        if (progressCount) {
            progressCount.textContent = `${completed}/${total}`;
        }
        
        console.log('Topic:', topicId, 'Progress:', topicProgress, 'Completed:', completed, 'Total:', total, 'Percentage:', percentage);
    });
}



// บันทึกความคืบหน้า
async function saveProgress() {
    try {
        // บันทึก localStorage
        localStorage.setItem(`learningProgress_${currentUser}`, JSON.stringify(progress));
        
        // ส่งไป server
        await sendProgressToPython();
        
        console.log('✅ Progress saved successfully');
    } catch (error) {
        console.error('❌ Error saving progress:', error);
    }
}

// โหลด progress ของผู้ใช้
function loadProgress() {
    progress = JSON.parse(JSON.stringify(defaultProgress)); // สร้าง base ใหม่
    const saved = localStorage.getItem(`learningProgress_${currentUser}`);
    if(saved){
        const savedProgress = JSON.parse(saved);
        for(const t in savedProgress){
            if(progress[t]){
                progress[t] = {...progress[t], ...savedProgress[t]}; // merge step ต่อ step
            }
        }
    }
}

// ส่งข้อมูลไป Python API
async function sendProgressToPython(){
    try{
        await fetch(`/api/progress`, {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({username: currentUser, progress: progress})
        });
    } catch(err){
        console.log('ไม่สามารถส่ง progress ไป server ได้', err);
    }
}

// โหลดความคืบหน้าจาก Python API
async function loadProgressFromPython() {
    try {
        console.log('Loading progress from server for user:', currentUser);
        
        const response = await fetch(`/api/progress?username=${currentUser}`);
        if (response.ok) {
            const data = await response.json();
            console.log('Received data from server:', data);
            
            if(data.success && data.progress){
                const validSteps = ['pretest', 'learn', 'posttest'];

                // ✅ สร้าง progress ใหม่จาก default
                progress = JSON.parse(JSON.stringify(defaultProgress));

                // ✅ merge ข้อมูลจาก server
                for (const t in data.progress) {
                    if (progress[t] && typeof data.progress[t] === 'object') {
                        validSteps.forEach(step => {
                            if(data.progress[t][step] === true){
                                progress[t][step] = true;
                            }
                        });
                    }
                }
                
                console.log('Progress loaded from server:', progress);
                return true; // ✅ บอกว่าโหลดสำเร็จ
            } else {
                console.log('Invalid data from server, loading from localStorage');
                loadProgress();
                return false;
            }
        } else {
            console.log('Server response not OK, loading from localStorage');
            loadProgress();
            return false;
        }
    } catch(err){
        console.error('โหลด progress จาก server ไม่ได้', err);
        loadProgress();
        return false;
    }
}