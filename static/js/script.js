document.addEventListener('DOMContentLoaded', function() {
    const addToCartButtons = document.querySelectorAll('.add-to-cart-btn');
    const removeCartButtons = document.querySelectorAll('.remove-from-cart-btn'); 
    const cartCountSpan = document.getElementById('cart-count');
    const cartTotalDisplay = document.getElementById('cart-total-display'); 

    
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    
    addToCartButtons.forEach(button => {
        button.addEventListener('click', function() {
            const productId = this.dataset.productId;
            const quantity = 1;

            fetch('/add_to_cart/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    productId: productId,
                    quantity: quantity
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    if (cartCountSpan) {
                        cartCountSpan.textContent = data.cart_count;
                    }
                    alert('Product added to cart!');
                    
                } else {
                    alert('Error adding to cart: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while adding to cart.');
            });
        });
    });

    
    removeCartButtons.forEach(button => {
        button.addEventListener('click', function() {
            const productId = this.dataset.productId;
            
            if (!confirm('Are you sure you want to remove this item from your cart?')) {
                return; 
            }

            fetch('/remove_from_cart/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    productId: productId
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    if (cartCountSpan) {
                        cartCountSpan.textContent = data.cart_count; 
                    }
                    if (cartTotalDisplay) {
                        cartTotalDisplay.textContent = parseFloat(data.new_total_price).toFixed(2); 
                    }

                    
                    const rowToRemove = document.getElementById(`cart-item-${productId}`);
                    if (rowToRemove) {
                        rowToRemove.remove();
                    }

                    
                    if (data.cart_count === 0) {
                        const cartTable = document.querySelector('.cart-table');
                        const cartSummaryBottom = document.querySelector('.cart-summary-bottom');
                        const cartPageContent = document.querySelector('.cart-page-content');

                        if (cartTable) cartTable.remove();
                        if (cartSummaryBottom) cartSummaryBottom.remove();
                        if (cartPageContent && !cartPageContent.querySelector('p')) { // Check if there's no existing empty message
                            cartPageContent.innerHTML += '<p>Your cart is empty. <a href="/shop/">Start shopping!</a></p>'; // Update as per your project's index url
                        }
                    }
                    alert('Product removed from cart!');
                } else {
                    alert('Error removing from cart: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while removing from cart.');
            });
        });
    });

});