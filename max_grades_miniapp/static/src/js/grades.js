// Grades page JavaScript
function initGradeSelects() {
    // Заполняем выпадающие списки оценок
    const gradeSelects = document.querySelectorAll('.grade-select');
    gradeSelects.forEach(select => {
        const currentValue = select.dataset.currentValue;
        let html = '<option value="">-</option>';
        [5, 4, 3, 2].forEach(v => {
            const sel = currentValue && parseFloat(currentValue) == v ? 'selected' : '';
            html += `<option ${sel}>&nbsp;&nbsp;${v}</option>`;
        });
        select.innerHTML = html;
    });
    
    // Выделяем текущие значения в attendance select
    const attendSelects = document.querySelectorAll('.attend-select');
    attendSelects.forEach(select => {
        const currentValue = select.dataset.currentValue;
        if (currentValue) {
            const option = select.querySelector(`option[value="${currentValue}"]`);
            if (option) option.selected = true;
        }
    });
}

function saveGrades() {
    const rows = document.querySelectorAll('.student-row');
    const grades = [];
    
    rows.forEach(row => {
        const studentId = row.dataset.studentId;
        const selects = row.querySelectorAll('.grade-select');
        const attendSelect = row.querySelector('.attend-select');
        
        grades.push({
            student_id: parseInt(studentId),
            attendance_type_id: attendSelect ? parseInt(attendSelect.value) : false,
            grade_1: selects[0] ? (selects[0].value || null) : null,
            grade_2: selects[1] ? (selects[1].value || null) : null,
            grade_3: selects[2] ? (selects[2].value || null) : null
        });
    });

    // Получаем lesson_id из URL
    const pathParts = window.location.pathname.split('/');
    const lessonId = pathParts[pathParts.length - 1];

    fetch('/max/grades/lesson/' + lessonId + '/grades', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRF-TOKEN': getCsrfToken()
        },
        body: JSON.stringify({grades})
    })
    .then(handleResponse)
    .then(function(result) {
        alert(result.success ? 'Сохранено!' : 'Ошибка: ' + result.error);
    })
    .catch(handleError);
}

function goBack() {
    window.location.href = '/max/grades/lessons';
}

// Инициализация Telegram WebApp и заполнение select'ов
document.addEventListener('DOMContentLoaded', function() {
    if (window.Telegram && window.Telegram.WebApp) {
        window.Telegram.WebApp.ready();
        window.Telegram.WebApp.expand();
    }
    initGradeSelects();
});
