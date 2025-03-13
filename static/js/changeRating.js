let selectedRating = 0;

function previewRating(value) {
    const stars = document.querySelectorAll('.star');
    stars.forEach((star, index) => {
        if (index < value) {
            star.textContent = '★';
        } else {
            star.textContent = '☆';
        }
    });
}

function resetRating() {
    previewRating(selectedRating);
}

function submitRating(value, id) {

    selectedRating = value;
    book_id=id;
    // Отправка данных рейтинга на сервер Flask
    $.ajax({
    url: '/submit_rating',
    method: 'POST',
    data: {
        'rating': selectedRating,
        'book_id': book_id
    },
    success: function(response) {
        if (response.status && response.status === "not_logged_in") {
            window.location.href = "/loginForm";  // Перенаправление на страницу входа
        } else {
            console.log(response.message);
            const notification = document.getElementById('notification');
            notification.style.display = 'block';
            setTimeout(() => {
                notification.style.display = 'none';
            }, 3000);
        }
    }
    });
    
    const notification = document.getElementById('notification');
    notification.style.display = 'block';
    setTimeout(() => {
        notification.style.display = 'none';
    }, 3000);
}

function resetToZero() {
    selectedRating = 0;
    const stars = document.querySelectorAll('.star');
    stars.forEach(star => {
        star.textContent = '☆';
    });
    const notification = document.getElementById('notification');
    notification.style.display = 'block';
    setTimeout(() => {
        notification.style.display = 'none';
        notification.textContent = 'Рейтинг додано';
    }, 3000);
}
document.addEventListener('DOMContentLoaded', function() {
    const ratingContainer = document.querySelector('.rating');
    const userRating = parseInt(ratingContainer.getAttribute('data-user-rating'));

    // Якщо рейтинг користувача більше 0, встановлюємо його
    if (userRating > 0) {
        previewRating(userRating);
        selectedRating = userRating;
    }
});