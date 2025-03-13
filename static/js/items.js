// Функция для получения данных о товаре и заполнения формы
function fetchProductDataAndFillForm(productId) {
  fetch(`/get_product_data/${productId}`)
    .then(response => response.json())
    .then(data => {
      const form = document.getElementById(`edit-product-form-${productId}`);
      form.querySelector('input[name="title"]').value = data.title;
      form.querySelector('input[name="author"]').value = data.author;
      form.querySelector('textarea[name="description"]').value = data.description;
      form.querySelector('input[name="price"]').value = data.price;
      form.querySelector('input[name="image_url"]').value = data.image_url;

      const genreList = document.getElementById(`genre-list-${productId}`);
      genreList.innerHTML = '';
      data.genre_ids.forEach(genreId => {
        const genre = allGenres.find(g => g.id === genreId);
        if (genre) {
          const genreItem = document.createElement('div');
          genreItem.className = 'genre-item';
          genreItem.dataset.genreId = genre.id;
          genreItem.textContent = genre.name;
		  genreItem.dataset.productId = productId;
          const removeButton = document.createElement('button');
          removeButton.type = 'button';
          removeButton.className = 'remove-genre';
          removeButton.textContent = '-';
          removeButton.addEventListener('click', function() {
            genreItem.remove();
          });

          genreItem.appendChild(removeButton);
          genreList.appendChild(genreItem);
        }
      });

      const genreSelect = document.getElementById(`genre-select-${productId}`);
      genreSelect.innerHTML = '';
      allGenres.forEach(genre => {
        if (!data.genre_ids.includes(genre.id)) {
          const option = document.createElement('option');
          option.value = genre.id;
          option.textContent = genre.name;
          genreSelect.appendChild(option);
        }
      });
    })
    .catch(error => {
      console.error('Error fetching product data:', error);
    });
}

// При нажатии на кнопку "Редактировать", вызываем эту функцию
function showEditForm(productId) {
  fetchProductDataAndFillForm(productId);
  const formToDisplay = document.getElementById(`edit-product-form-${productId}`);
  formToDisplay.style.display = 'block';
  formToDisplay.scrollIntoView();
}

// Функция для добавления жанра к товару
function addGenreToProduct(productId, genreId) {
  fetch(`/add-genre-to-product/${productId}/${genreId}`, { method: 'POST' })
    .then(response => response.json())
    .then(data => {
      
      // Обновите интерфейс пользователя здесь, если необходимо
    })
    .catch(error => {
      console.error('Error adding genre:', error);
    });
}

// Функция для удаления жанра из товара
function removeGenreFromProduct(productId, genreId) {
  fetch(`/remove-genre-from-product/${productId}/${genreId}`, { method: 'POST' })
    .then(response => response.json())
    .then(data => {
      
      // Обновите интерфейс пользователя здесь, если необходимо
    })
    .catch(error => {
      console.error('Error removing genre:', error);
    });
}

// Обработчик для кнопки добавления жанра
document.addEventListener('click', function(event) {
  if (event.target.matches('.add-genre')) {
    const productId = event.target.id.split('-').pop();
    const genreSelect = document.getElementById(`genre-select-${productId}`);
    const selectedGenreId = genreSelect.value;
    const selectedGenreText = genreSelect.options[genreSelect.selectedIndex].text;

    addGenreToProduct(productId, selectedGenreId);

    const genreList = document.getElementById(`genre-list-${productId}`);
    const genreItem = document.createElement('div');
    genreItem.className = 'genre-item';
	genreItem.dataset.productId = productId;
    genreItem.dataset.genreId = selectedGenreId;
    genreItem.textContent = selectedGenreText;

    const removeButton = document.createElement('button');
    removeButton.type = 'button';
    removeButton.className = 'remove-genre';
    removeButton.textContent = '-';
    removeButton.addEventListener('click', function() {
      removeGenreFromProduct(productId, selectedGenreId);
      genreItem.remove();
    });

    genreItem.appendChild(removeButton);
    genreList.appendChild(genreItem);

    genreSelect.remove(genreSelect.selectedIndex);
  }
});

document.addEventListener('click', function(event) {
  if (event.target.matches('.remove-genre')) {
    const genreItem = event.target.closest('.genre-item');
    if (genreItem) {
      const productId = genreItem.dataset.productId;
      const genreId = genreItem.dataset.genreId;

      if (productId && genreId) {
        removeGenreFromProduct(productId, genreId);
        genreItem.remove();
      } else {
        console.error('Product ID or Genre ID not found');
      }
    }
  }
});

// Загрузка всех жанров при загрузке страницы
let allGenres = [];
function fetchAllGenres() {
  fetch('/get-all-genres')
    .then(response => response.json())
    .then(data => {
      allGenres = data;
    })
    .catch(error => {
      console.error('Error fetching genres:', error);
    });
}
function cancelEdit_book(productId) {
  const formToHide = document.getElementById(`edit-product-form-${productId}`);
   if (formToHide) {
    formToHide.style.display = 'none';
  } else {
    console.error(`Form with ID edit-product-form-${productId} not found.`);
  }
}
function deleteBook(bookId) {
  if (confirm('Ви впевнені, що хочете видалити цю книгу (це не можливо відмінити)? ')) {
    fetch(`/delete-book/${bookId}`, { method: 'POST' })
      .then(response => {
        if (response.ok) {
          return response.json();
        }
        throw new Error('Проблема при видаленні книги');
      })
      .then(data => {
       
        window.location.reload(); // или перенаправьте на другую страницу 
      })
      .catch(error => {
        console.error('Error:', error);
      });
  }
}
document.addEventListener('DOMContentLoaded', fetchAllGenres);