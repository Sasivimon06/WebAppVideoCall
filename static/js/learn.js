// สถานะการเรียน
let progress = {
    topic1: { pretest: false, learn: false, posttest: false },
    topic2: { pretest: false, learn: false, posttest: false },
    topic3: { pretest: false, learn: false, posttest: false }
};

// ข้อมูลหัวข้อ
const topics = {
    topic1: { title: 'การล้างมือ', description: 'เรียนรู้ความสำคัญของการล้างมือและวิธีการล้างมือที่ถูกต้อง' },
    topic2: { title: 'การนอนหลับ', description: 'เรียนรู้ความสำคัญของการนอนหลับและวิธีการนอนที่มีคุณภาพ' },
    topic3: { title: 'โภชนาการ', description: 'เรียนรู้หลักการโภชนาการและการรับประทานอาหารเพื่อสุขภาพ' }
};

// ตัวแปรสถานะปัจจุบัน
let currentTopic = '';
let currentStep = '';

// เริ่มต้น
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    loadProgressFromPython(); // โหลด progress จาก server
    loadProgress(); // โหลด progress จาก localStorage
    restoreLastPage(); // โหลดหน้าปัจจุบัน
    setTimeout(updateProgressBars, 100);
});

// ฟังก์ชันบันทึกหน้าเดิม
function restoreLastPage() {
    const savedPage = localStorage.getItem('currentPage');
    const savedTopic = localStorage.getItem('currentTopic');
    const savedStep = localStorage.getItem('currentStep');

    if (savedPage) {
        if (savedPage === 'home-page') {
            showHomePage();
        } else if (savedPage === 'topic-page' && savedTopic) {
            showTopicPage(savedTopic);
        } else if (savedPage === 'step-page' && savedTopic && savedStep) {
            showTopicPage(savedTopic);
            showStepPage(savedStep);
        } else {
            showHomePage();
        }
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
    updateProgressBars();

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
function completeStep(stepId) {
    progress[currentTopic][stepId] = true;
    saveProgress();

    let message = '';
    switch(stepId) {
        case 'pretest': message = 'ส่งคำตอบแบบทดสอบก่อนเรียนสำเร็จ!'; break;
        case 'learn': message = 'เรียนจบแล้ว! คุณสามารถทำแบบทดสอบหลังเรียนได้'; break;
        case 'posttest': message = 'ส่งคำตอบสำเร็จ! คุณได้เรียนจบหัวข้อนี้แล้ว'; break;
    }

    alert(message);
    showTopicPage();
}

// อัพเดทสถานะขั้นตอน
function updateStepStatus() {
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
    document.querySelectorAll('.topic-card').forEach(card => {
        const topicId = card.getAttribute('data-topic');
        const progressBar = card.querySelector('.progress');
        const progressCount = card.querySelector('.progress-count');

        const completed = Object.values(progress[topicId]).filter(v => v).length;
        const total = Object.values(progress[topicId]).length; // 3
        const percentage = (completed / total) * 100;

        // อัพเดทแถบ
        progressBar.style.width = percentage + '%';
        progressBar.setAttribute('data-progress', percentage);

        // อัพเดทตัวเลข
        if (progressCount) {
            progressCount.textContent = `${completed}/${total}`;
        }
    });
}

// บันทึกความคืบหน้า
function saveProgress() {
    try {
        localStorage.setItem('learningProgress', JSON.stringify(progress));
        sendProgressToPython();
    } catch (error) {
        console.error('Error saving progress:', error);
    }
}

// โหลดความคืบหน้า
function loadProgress() {
    try {
        const saved = localStorage.getItem('learningProgress');
        if (saved) progress = JSON.parse(saved);
    } catch (error) {
        console.error('Error loading progress:', error);
    }
}

// ส่งข้อมูลไป Python API
async function sendProgressToPython() {
    try {
        await fetch('/api/progress', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ progress: progress, timestamp: new Date().toISOString() })
        });
    } catch (error) {
        console.log('Could not save to server, using local storage only');
    }
}

// โหลดความคืบหน้าจาก Python API
async function loadProgressFromPython() {
    try {
        const response = await fetch('/api/progress');
        if (response.ok) {
            const data = await response.json();
            progress = data.progress || progress;
        }
    } catch {
        loadProgress();
    }
}
