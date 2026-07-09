// Grades App JavaScript - common utilities
function getCsrfToken() {
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrf_token='));
    return cookieValue ? cookieValue.split('=')[1] : '';
}

// Инициализация Telegram WebApp
document.addEventListener('DOMContentLoaded', function() {
    if (window.Telegram && window.Telegram.WebApp) {
        window.Telegram.WebApp.ready();
        window.Telegram.WebApp.expand();
    }

    // Обработчики для дашборда
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            window.location.href = '/max/grades/logout';
        });
    }

    document.querySelectorAll('.module-card-wrapper').forEach(el => {
        el.addEventListener('click', function() {
            const moduleId = this.dataset.moduleId;
            if (moduleId === 'schedule') {
                window.location.href = '/max/grades/lessons';
            }
        });
    });

    // Обработчики для страницы входа
    const loginBtn = document.getElementById('login-btn');
    if (loginBtn) {
        loginBtn.addEventListener('click', gradesLogin);
    }

    // Обработчики для страницы уроков
    const backBtn = document.getElementById('back-btn');
    if (backBtn) {
        backBtn.addEventListener('click', () => {
            localStorage.removeItem('grades_date');
            localStorage.removeItem('grades_faculty');
            window.location.href = '/max/grades/dashboard';
        });
    }

    const saveGradesBtn = document.getElementById('save-grades-btn');
    if (saveGradesBtn) {
        saveGradesBtn.addEventListener('click', saveGrades);
    }

    const backToLessonsBtn = document.getElementById('back-to-lessons-btn');
    if (backToLessonsBtn) {
        backToLessonsBtn.addEventListener('click', () => {
            window.location.href = '/max/grades/lessons';
        });
    }

    // Функции для страницы входа
    window.gradesLogin = function() {
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        fetch('/max/grades/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-TOKEN': getCsrfToken()
            },
            body: JSON.stringify({email, password})
        })
        .then(r => r.json()).then(function(result) {
            if (result.error) {
                document.getElementById('error-msg').textContent = result.error;
                document.getElementById('error-msg').classList.remove('d-none');
            } else {
                window.location.href = '/max/grades/dashboard';
            }
        });
    };

    // Функции для страницы уроков
    const datePicker = document.getElementById('date-picker');
    if (datePicker) {
        const savedDate = localStorage.getItem('grades_date');
        if (savedDate) datePicker.value = savedDate;
        datePicker.addEventListener('change', function() {
            localStorage.setItem('grades_date', this.value);
            loadLessons();
        });
    }

    const facultyFilter = document.getElementById('faculty-filter');
    if (facultyFilter) {
        const savedFaculty = localStorage.getItem('grades_faculty');
        if (savedFaculty) facultyFilter.value = savedFaculty;
        facultyFilter.addEventListener('change', function() {
            localStorage.setItem('grades_faculty', this.value);
            loadLessons();
        });
    }

    window.loadLessons = function() {
        const date = document.getElementById('date-picker').value;
        const facultyId = document.getElementById('faculty-filter')?.value || '';
        let url = '/max/grades/api/lessons?date=' + date;
        if (facultyId) url += '&faculty_id=' + facultyId;
        fetch(url, {
            method: 'GET',
            headers: {'Content-Type': 'application/json', 'X-CSRF-TOKEN': getCsrfToken()}
        })
        .then(r => r.json()).then(function(result) {
            let html = '';
            if (result.lessons && result.lessons.length) {
                result.lessons.forEach(l => {
                    let timing = l.timing || '';
                    html += '<button class="list-group-item list-group-item-action open-lesson" data-lesson-id="' + l.id + '">' +
                        '<div class="d-flex justify-content-between"><strong>' + l.subject + '</strong>' +
                        '<small class="text-muted">' + l.batch + '</small></div>' +
                        (timing ? '<small class="text-muted">' + timing + '</small>' : '') + '</button>';
                });
            } else {
                html = '<p class="text-muted">Нет занятий</p>';
            }
            document.getElementById('lessons-list').innerHTML = html;

            // Обработчики открытия урока
            document.querySelectorAll('.open-lesson').forEach(btn => {
                btn.addEventListener('click', function() {
                    window.location.href = '/max/grades/lesson/' + this.dataset.lessonId;
                });
            });
        });
    };

    // Функции для страницы оценок
    window.saveGrades = function() {
        const rows = document.querySelectorAll('.student-row');
        const grades = [];

        // Заполняем пустые select-ы значениями
        document.querySelectorAll('.grade-select').forEach(select => {
            if (!select.innerHTML) {
                let html = '<option value="">-</option>';
                [5,4,3,2].forEach(v => {
                    const sel = select.dataset.currentValue && parseFloat(select.dataset.currentValue) == v ? 'selected' : '';
                    html += '<option ' + sel + '>&nbsp;&nbsp;' + v + '</option>';
                });
                select.innerHTML = html;
            }
        });

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

        const lessonId = window.location.pathname.match(/\/max\/grades\/lesson\/(\d+)/);
        if (!lessonId) return;

        fetch('/max/grades/lesson/' + lessonId[1] + '/grades', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-TOKEN': getCsrfToken()
            },
            body: JSON.stringify({grades})
        })
        .then(r => r.json()).then(function(result) {
            alert(result.success ? 'Сохранено!' : 'Ошибка: ' + result.error);
        });
    };
});