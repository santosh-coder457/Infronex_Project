from django.contrib import admin
from .models import Product, Cart, CartItem
from .models import Payment, Order
from .models import Payment, Order, OrderItem, Product

# Register your models here.
admin.site.register(Product)
admin.site.register(Cart)
admin.site.register(CartItem)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'order', 'transaction_id', 'amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('transaction_id', 'user__username', 'order__id')
    raw_id_fields = ('user', 'order') 

    def display_products(self, obj):
        if obj.order:
            return ", ".join([item.product.name for item in obj.order.items.all()])
        return "N/A"
    display_products.short_description = "Products" # Column header in admin list