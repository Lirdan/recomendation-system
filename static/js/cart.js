/**
 * Script for managing the cart modal window and its contents.
 *
 * Features:
 * - Opens the cart modal when the cart button is clicked
 * - Fetches current cart items from the Flask server via /cart_data
 * - Displays the list of cart items with their names and prices
 * - Allows users to remove items from the cart dynamically via /remove_from_cart
 * - Updates total price and checkout button status on any change
 * - Handles closing the modal (both via close button and outside click)
 *
 * Dependencies:
 * - HTML elements with IDs: cartButton, cartModal, cartItems, totalPrice, checkout-button
 * - Flask backend routes: /cart_data, /remove_from_cart
 */
document.addEventListener("DOMContentLoaded", function() {
  // DOM references
  var cartButton = document.getElementById("cartButton");
  var cartModal = document.getElementById("cartModal");
  var closeButton = document.getElementsByClassName("close")[0];
  var cartItems = document.getElementById("cartItems");
  var totalPrice = document.getElementById("totalPrice");
  var checkoutButton = document.getElementById("checkout-button");
  // Open cart modal and populate items
  cartButton.addEventListener("click", function() {
  cartModal.style.display = "block";
	
    // Fetch cart items from Flask server
    fetch("/cart_data") 
      .then(response => response.json())
      .then(data => {
        // Clear previous items
        cartItems.innerHTML = "";

        // Render each cart item
        data.items.forEach(item => {
          var listItem = document.createElement("li");
          listItem.innerHTML = item.name + " - " + item.price;
          var removeButton = document.createElement("button");
          removeButton.innerHTML = "-";
	  removeButton.classList.add("removeButtonClass");
          // Handle click on remove button
          removeButton.addEventListener("click", function() {
           					  
  // Send request to Flask to remove item
  fetch("/remove_from_cart", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ id: item.id }) // Send item ID to remove
  })
    .then(response => response.json())
    .then(data => {
     // If the product has been successfully deleted, update the list of products and the total cost
      if (data.message === "Товар успішно видалео з кошика.") {
        listItem.remove(); // Remove item from DOM
        updateTotalPrice(); // Update price and checkout state
      }
    })
    .catch(error => {
      console.error("Ошибка удаления товара из корзины:", error);
    });								
          });	
// Function to recalculate and update total price
function updateTotalPrice() {
  // Send a request to the Flask server to receive the bucket data
  // and update the total cost
  fetch("/cart_data")
    .then(response => response.json())
    .then(data => {
      // Update checkout button
      totalPrice.innerHTML = data.totalPrice;
      checkCartEmpty();
    })
    .catch(error => {
      console.error("Ошибка получения данных корзины:", error);
    });
}
          listItem.appendChild(removeButton);
          cartItems.appendChild(listItem);
        });

        // Set total price
        totalPrice.innerHTML = data.totalPrice;
      })
      .catch(error => {
        console.error("Ошибка получения данных корзины:", error);
      });
  });

  
  // Enable/disable checkout button based on cart contents
  function checkCartEmpty() {
    fetch("/cart_data")
      .then(response => response.json())
      .then(data => {
        if (data.items.length === 0) {
			 checkoutButton.removeAttribute("href"); // Remove href attribute
          checkoutButton.classList.add("disabled"); // Add disabled class for styling
        } else {
			          checkoutButton.setAttribute("href", "/checkout"); // Set href attribute to a valid value
          checkoutButton.classList.remove("disabled"); // Remove disabled class
        }
		console.log("------")
      })
      .catch(error => {
        console.error("Ошибка получения данных корзины:", error);
      });
  }
  

  
  // Close modal when X is clicked
  closeButton.addEventListener("click", function() {
    cartModal.style.display = "none";
  });

  // Close modal when clicking outside the modal
  window.addEventListener("click", function(event) {
    if (event.target == cartModal) {
      cartModal.style.display = "none";
    }
  });

   // Initial state check on load
  checkCartEmpty();
});


