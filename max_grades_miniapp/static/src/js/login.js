// Login page JavaScript
function gradesLogin() {
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    if (!email || !password) {
        document.getElementById('error-msg').textContent = 'Email и пароль обязательны';
        document.getElementById('error-msg').classList.remove('d-none');
        return;
    }

    fetch('/max/grades/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRF-TOKEN': getCsrfToken()
        },
        body: JSON.stringify({email, password})
    })
    .then(handleResponse)
    .then(function(result) {
        if (result.error) {
            document.getElementById('error-msg').textContent = result.error;
            document.getElementById('error-msg').classList.remove('d-none');
        } else {
            window.location.href = '/max/grades/dashboard';
        }
    })
    .catch(handleError);
}

function handleResponse(response) {
    if (!response.ok) {
        return response.json().then(err => {
            throw new Error(err.error || 'Неизвестная ошибка');
        });
    }
    return response.json();
}

function handleError(error) {
    const errorMsg = document.getElementById('error-msg');
    if (errorMsg) {
        errorMsg.textContent = error.message;
        errorMsg.classList.remove('d-none');
    }
}

// Telegram WebApp initialization
document.addEventListener('DOMContentLoaded', function() {
    if (window.Telegram && window.Telegram.WebApp) {
        window.Telegram.WebApp.ready();
        window.Telegram.WebApp.expand();
    }
});
