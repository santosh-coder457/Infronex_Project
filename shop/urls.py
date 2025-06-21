from django.urls import path
from . import views

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('add_to_cart/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.view_cart, name='view_cart'),
    path('remove_from_cart/', views.remove_from_cart, name='remove_from_cart'), # ADD THIS LINE
    path('checkout/', views.checkout, name='checkout'),
]