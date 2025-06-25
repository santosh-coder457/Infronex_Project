from django.urls import path
from . import views

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('add_to_cart/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.view_cart, name='view_cart'),
    path('remove_from_cart/', views.remove_from_cart, name='remove_from_cart'), 
    path('checkout/', views.checkout, name='checkout'),
    path('razorpay/callback/', views.razorpay_callback, name='razorpay_callback'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('checkout/success/', views.checkout_success, name='checkout_success'),
    path('checkout/failed/', views.checkout_failed, name='checkout_failed'),
]
