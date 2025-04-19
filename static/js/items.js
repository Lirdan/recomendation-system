/**
 * Admin Product Management Script
 *
 * Features:
 * - Fetches book data and fills edit form dynamically
 * - Allows adding and removing genres to/from a book
 * - Sends genre update requests to the server
 * - Handles book deletion
 * - Loads all genres on page load
 */

/**
 * Fetch product data by ID and fill its edit form.
 * 
 * @param {number} productId - The ID of the product to fetch
 */
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
      // Fill current genres
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
       // Populate genre <select> with genres not already assigned
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

/**
 * Shows the edit form for a given product.
 * @param {number} productId - The product to show the form for
 */
function showEditForm(productId) {
  fetchProductDataAndFillForm(productId);
  const formToDisplay = document.getElementById(`edit-product-form-${productId}`);
  formToDisplay.style.display = 'block';
  formToDisplay.scrollIntoView();
}

/**
 * Sends request to Flask to add genre to a product.
 */
function addGenreToProduct(productId, genreId) {
  fetch(`/add-genre-to-product/${productId}/${genreId}`, { method: 'POST' })
    .then(response => response.json())
    .then(data => {
      
    })
    .catch(error => {
      console.error('Error adding genre:', error);
    });
}

/**
 * Sends request to Flask to remove genre from a product.
 */
function removeGenreFromProduct(productId, genreId) {
  fetch(`/remove-genre-from-product/${productId}/${genreId}`, { method: 'POST' })
    .then(response => response.json())
    .then(data => {
      
    })
    .catch(error => {
      console.error('Error removing genre:', error);
    });
}

/**
 * Event delegation for adding genres to a product.
 */
document.addEventListener('click', function(event) {
  if (event.target.matches('.add-genre')) {
    const productId = event.target.id.split('-').pop();
    const genreSelect = document.getElementById(`genre-select-${productId}`);
    const selectedGenreId = genreSelect.value;
    const selectedGenreText = genreSelect.options[genreSelect.selectedIndex].text;

    addGenreToProduct(productId, selectedGenreId);
    // Update UI with newly added genre
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
      genreItem.remove(); // Remove from dropdown
    });

    genreItem.appendChild(removeButton);
    genreList.appendChild(genreItem);

    genreSelect.remove(genreSelect.selectedIndex);
  }
});

/**
 * Event delegation for removing genres from product.
 */
document.addEventListener('click', function(event) {
  if (event.target.matches('.remove-genre')) {
    const genreItem = event.target.closest('.genre-item');
    if (genreItem) {
      const productId = genreItem.dataset.productId;
      const genreId = genreItem.dataset.genreId;

      if (productId && genreId) {
        removeGenreFromProduct(productId, genreId);
        genreItem.remove(); // Update UI
      } else {
        console.error('Product ID or Genre ID not found');
      }
    }
  }
});

/**
 * Load all available genres from the server and store them.
 */
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
/**
 * Hides the edit form for a product without saving.
 */
function cancelEdit_book(productId) {
  const formToHide = document.getElementById(`edit-product-form-${productId}`);
   if (formToHide) {
    formToHide.style.display = 'none';
  } else {
    console.error(`Form with ID edit-product-form-${productId} not found.`);
  }
}
/**
 * Deletes the selected book after confirmation.
 */
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
       
        window.location.reload(); // Refresh page after deletion
      })
      .catch(error => {
        console.error('Error:', error);
      });
  }
}
// Fetch genres once DOM is fully loaded
document.addEventListener('DOMContentLoaded', fetchAllGenres);
