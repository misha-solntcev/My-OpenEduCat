// Lessons page JavaScript
let currentDate = null;
let currentFaculty = null;

// Загрузка уроков
function loadLessons() {
    const date = document.getElementById('date-picker').value;
    const facultyId = document.getElementById('faculty-filter')?.value || '';
    let url = '/max/grades/api/lessons?date=' + date;
    if (facultyId) {
        url += '&faculty_id=' + facultyId;
    }

    fetch(url, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRF-TOKEN': getCsrfToken()
        }
    })
    .then(handleResponse)
    .then(function(result) {
        renderLessons(result.lessons || []);
    })
    .catch(handleError);
}

// Отображение списка уроков
function renderLessons(lessons) {
    const container = document.getElementById('lessons-list');
    let html = '';
    
    if (lessons && lessons.length) {
        lessons.forEach(l => {
            let timing = l.timing || '';
            html += '<button class="list-group-item list-group-item-action" onclick="openLesson(' + l.id + ')">' +
                '<div class="d-flex justify-content-between"><strong>' + l.subject + '</strong>' +
                '<small class="text-muted">' + l.batch + '</small></div>' +
                (timing ? '<small class="text-muted">' + timing + '</small>' : '') + '</button>';
        });
    } else {
        html = '<p class="text-muted">Нет занятий</p>';
    }
    
    container.innerHTML = html;
}

// Открытие урока
function openLesson(lessonId) {
    window.location.href = '/max/grades/lesson/' + lessonId;
}

// Возврат назад
function goBack() {
    localStorage.removeItem('grades_date');
    localStorage.removeItem('grades_faculty');
    window.location.href = '/max/grades/dashboard';
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    const savedDate = localStorage.getItem('grades_date');
    const savedFaculty = localStorage.getItem('grades_faculty');
    
    if (savedDate) {
        document.getElementById('date-picker').value = savedDate;
    }
    
    const facultyFilter = document.getElementById('faculty-filter');
    if (facultyFilter && savedFaculty) {
        facultyFilter.value = savedFaculty;
    }
    
    loadLessons();
    
    // Обработчики событий
    document.getElementById('date-picker').addEventListener('change', function() {
        localStorage.setItem('grades_date', this.value);
        loadLessons();
    });
    
    if (facultyFilter) {
        facultyFilter.addEventListener('change', function() {
            localStorage.setItem('grades_faculty', this.value);
            loadLessons();
        });
    }
});

// Обработка bfcache (для Telegram WebApp)
window.addEventListener('pageshow', function(event) {
    if (event.persisted) {
        const savedDate = localStorage.getItem('grades_date');
        const savedFaculty = localStorage.getItem('grades_faculty');
        
        if (savedDate) {
            document.getElementById('date-picker').value = savedDate;
        }
        
        const facultyFilter = document.getElementById('faculty-filter');
        if (facultyFilter && savedFaculty) {
            facultyFilter.value = savedFaculty;
        }
    }
});
