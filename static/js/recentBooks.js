/**
 * Script to handle dynamic display of all purchased books on profile page.
 *
 * Features:
 * - Loads all purchased books via AJAX when "Show All" is clicked
 * - Hides the button after loading, and shows a "Hide" button
 * - Clicking "Hide" simply reloads the page to restore initial state
 */

window.onload = function() {
    // DOM elements
    const showAllBooksButton = document.getElementById('show-all-books');
    const hideBooksButton = document.getElementById('hide-books');
    const booksList = document.getElementById('recently-bought-books');
    // Show all purchased books
    showAllBooksButton.addEventListener('click', function() {
        fetch('/api/all-books') // Fetch books via Flask API
        .then(response => response.json())
        .then(data => {
	    // Clear the current list
            booksList.innerHTML = '';
            data.forEach(book => {
                let listItem = document.createElement('li');
                listItem.innerHTML = `
                    <a href="/productDescription?productId=${book[0]}">
					<img src="${book[4]}" alt="Обкладинка книги ${book[0]}" width="50" height="70">
                    <strong>${book[1]}</strong> автор: ${book[2]} - ${book[3]} ₴</a>
                `;
                booksList.appendChild(listItem);
            });
	    // Toggle button visibility
            showAllBooksButton.style.display = 'none';
            hideBooksButton.style.display = 'block';
        })
        .catch(error => {
            console.error('Error fetching books:', error);
        });
    });
    // Hide books by reloading the page
    hideBooksButton.addEventListener('click', function() {
        // Reset view to original state
        location.reload();
    });
};
