/**
 * Script for handling "Add to Cart" button functionality.
 * - Uses jQuery to listen for clicks on elements with class .addToCart
 * - Sends an AJAX POST request to the server to add the selected item to the user's cart
 * - If the user is not logged in, redirects to the login page
 * - If successful, activates the checkout button
 */
 $(document).ready(function() {
	 // Get the checkout button element
	 var checkoutButton = document.getElementById("checkout-button");
	// Attach a click event listener to all elements with the class .addToCart
    $('.addToCart').click(function(event) {
      event.preventDefault(); // Prevent default form submission or link behavior

      //var productID = $(this).data('product-id'); // Идентификатор товара
	  // Retrieve the product ID from the clicked button
	  var productID = $(this).attr('id');
	  console.log(productID)

      // Send asynchronous POST request to the server to add product to cart
      $.ajax({
        url: '/addToCart',
        type: 'POST',
        data: {
          product_id: productID, // Send product ID as POST data
        },
        success: function(response) {
        // Handle successful response from server
		  console.log(response)
		  if (response.redirect) {
        // If the server response includes a redirect URL (e.g., not logged in), go to it
		  window.location.href = response.redirect;}
		  // If the item was successfully added, enable the checkout button
		  checkoutButton.setAttribute("href", "/checkout"); // Set href attribute to a valid value
          checkoutButton.classList.remove("disabled"); // Remove 
		   
        },
        error: function(xhr, status, error) {
          // Обработка ошибки запроса
        }
      });
    });
  });
