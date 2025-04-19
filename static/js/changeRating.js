/**
 * Rating system for books
 * 
 * - Handles star preview on hover
 * - Submits selected rating via AJAX to the server
 * - Shows notification on successful submission
 * - Redirects to login if user is not authenticated
 * - Automatically loads user rating on page load
 */
let selectedRating = 0; // Stores the current selected rating

// Highlight stars up to the given value (for hover effect)
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

// Reset stars to reflect the selected rating
function resetRating() {
    previewRating(selectedRating);
}

// Submit rating for a book
function submitRating(value, id) {
    selectedRating = value;
    book_id=id;
    // Send AJAX POST request to Flask backend
    $.ajax({
    url: '/submit_rating',
    method: 'POST',
    data: {
        'rating': selectedRating,
        'book_id': book_id
    },
    success: function(response) {
        if (response.status && response.status === "not_logged_in") {
            window.location.href = "/loginForm";  // Redirect to login page if user is not logged in
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

// Reset selected rating to 0 and clear stars
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
// On page load, apply existing user rating if available
document.addEventListener('DOMContentLoaded', function() {
    const ratingContainer = document.querySelector('.rating');
    const userRating = parseInt(ratingContainer.getAttribute('data-user-rating'));

    // If the user's rating is greater than 0, Set It
    if (userRating > 0) {
        previewRating(userRating);
        selectedRating = userRating;
    }
});
