from django.db import models
from django.contrib.auth.models import User

class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    # Use CharField for image URL, as you're using external URLs or static paths
    image_url = models.CharField(max_length=500, blank=True, null=True)
    # image = models.ImageField(upload_to='products/', blank=True, null=True) # If you want to upload images

    def __str__(self):
        return self.name

class Cart(models.Model):
    # Cart linked to a User OR a session (for anonymous users)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.user:
            return f"Cart of {self.user.username}"
        return f"Guest Cart ({self.session_key})"

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        # Ensures that a product can only appear once in a given cart
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in {self.cart}"

    @property
    def total_price(self):
        return self.quantity * self.product.price