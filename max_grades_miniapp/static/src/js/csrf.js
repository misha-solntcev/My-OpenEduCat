// CSRF Token helper - общий для всех страниц
function getCsrfToken() {
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrf_token='));
    return cookieValue ? cookieValue.split('=')[1] : '';
}
