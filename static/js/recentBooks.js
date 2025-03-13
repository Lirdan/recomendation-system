window.onload = function() {
    const showAllBooksButton = document.getElementById('show-all-books');
    const hideBooksButton = document.getElementById('hide-books');
    const booksList = document.getElementById('recently-bought-books');

    showAllBooksButton.addEventListener('click', function() {
        fetch('/api/all-books')
        .then(response => response.json())
        .then(data => {
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
            showAllBooksButton.style.display = 'none';
            hideBooksButton.style.display = 'block';
        })
        .catch(error => {
            console.error('Error fetching books:', error);
        });
    });

    hideBooksButton.addEventListener('click', function() {
        // Здесь мы просто перезагружаем страницу, чтобы вернуться к первоначальному состоянию
        location.reload();
    });
};