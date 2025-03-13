document.addEventListener("DOMContentLoaded", function() {
  var cartButton = document.getElementById("cartButton");
  var cartModal = document.getElementById("cartModal");
  var closeButton = document.getElementsByClassName("close")[0];
  var cartItems = document.getElementById("cartItems");
  var totalPrice = document.getElementById("totalPrice");
  var checkoutButton = document.getElementById("checkout-button");
  cartButton.addEventListener("click", function() {
    cartModal.style.display = "block";
	
    // Отправить запрос на сервер Flask для получения данных корзины
    // и заполнить список товаров и общую стоимость
    fetch("/cart_data") 
      .then(response => response.json())
      .then(data => {
        // Очистить список товаров
        cartItems.innerHTML = "";

        // Заполнить список товаров
        data.items.forEach(item => {
          var listItem = document.createElement("li");
          listItem.innerHTML = item.name + " - " + item.price;
          var removeButton = document.createElement("button");
          removeButton.innerHTML = "-";
		  removeButton.classList.add("removeButtonClass");

          removeButton.addEventListener("click", function() {
           				
	
	  
  // Отправить запрос на сервер Flask для удаления товара
  fetch("/remove_from_cart", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ id: item.id }) // Передаем идентификатор товара, который нужно удалить
  })
    .then(response => response.json())
    .then(data => {
      // Если товар успешно удален, обновляем список товаров и общую стоимость
      if (data.message === "Товар успішно видалео з кошика.") {
        listItem.remove(); // Удаляем элемент из списка
        updateTotalPrice(); // Обновляем общую стоимость
      }
    })
    .catch(error => {
      console.error("Ошибка удаления товара из корзины:", error);
    });								
          });			  
		  function updateTotalPrice() {
  // Отправить запрос на сервер Flask для получения данных корзины
  // и обновить общую стоимость
  fetch("/cart_data")
    .then(response => response.json())
    .then(data => {
      // Обновить общую стоимость
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

        // Заполнить общую стоимость
        totalPrice.innerHTML = data.totalPrice;
      })
      .catch(error => {
        console.error("Ошибка получения данных корзины:", error);
      });
  });

  
  
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
  

  
  
  closeButton.addEventListener("click", function() {
    cartModal.style.display = "none";
  });

  window.addEventListener("click", function(event) {
    if (event.target == cartModal) {
      cartModal.style.display = "none";
    }
  });
  checkCartEmpty();
});


