 $(document).ready(function() {
	 var checkoutButton = document.getElementById("checkout-button");
    $('.addToCart').click(function(event) {
      event.preventDefault(); // Предотвращает переход по ссылке или отправку формы

      //var productID = $(this).data('product-id'); // Идентификатор товара
	  var productID = $(this).attr('id');
	  console.log(productID)
       // Текущий URL страницы

      // Отправка асинхронного запроса на сервер
      $.ajax({
        url: '/addToCart',
        type: 'POST',
        data: {
          product_id: productID,
        },
        success: function(response) {
          // Обработка успешного ответа от сервера
          // Обновление соответствующей части страницы с обновленными данными
		  console.log(response)
		  if (response.redirect) {
        // Manually redirect the user to the login page
		  window.location.href = response.redirect;}
		  
		  checkoutButton.setAttribute("href", "/checkout"); // Set href attribute to a valid value
          checkoutButton.classList.remove("disabled"); // Remove 
		   
        },
        error: function(xhr, status, error) {
          // Обработка ошибки запроса
        }
      });
    });
  });