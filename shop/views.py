from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import json
from django.conf import settings
import razorpay
import datetime 

from .models import Product, Cart, CartItem

# Initialize Razorpay client
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
client.set_app_details({"title": "Django E-commerce", "version": "1.0"})

def get_or_create_cart(request):
    """
    Helper function to get or create a cart for the current user or session.
    """
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        if request.session.session_key and not created:
            session_cart = Cart.objects.filter(session_key=request.session.session_key).exclude(user=request.user).first()
            if session_cart:
                for item in session_cart.items.all():
                    cart_item, created_item = CartItem.objects.get_or_create(cart=cart, product=item.product)
                    if not created_item:
                        cart_item.quantity += item.quantity
                    else:
                        cart_item.quantity = item.quantity
                    cart_item.save()
                session_cart.delete() 
                request.session.pop('cart_count', None) 
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key)

    request.session['cart_count'] = sum(item.quantity for item in cart.items.all())
    return cart

def checkout_success(request):
    return render(request, 'shop/checkout_success.html', {}) 

def product_list(request):
    products = Product.objects.all()
    get_or_create_cart(request)
    return render(request, 'shop/index.html', {'products': products})

def add_to_cart(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('productId')
            quantity = int(data.get('quantity', 1))

            product = get_object_or_404(Product, id=product_id)
            cart = get_or_create_cart(request)

            cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
            if not created:
                cart_item.quantity += quantity
            else:
                cart_item.quantity = quantity
            cart_item.save()

            request.session['cart_count'] = sum(item.quantity for item in cart.items.all())

            return JsonResponse({'success': True, 'cart_count': request.session['cart_count']})
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON.'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)

def view_cart(request):
    cart = get_or_create_cart(request)
    cart_items = cart.items.all()
    total_price = sum(item.total_price for item in cart_items)
    return render(request, 'shop/cart.html', {'cart_items': cart_items, 'total_price': total_price})

def remove_from_cart(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('productId')

            product = get_object_or_404(Product, id=product_id)
            cart = get_or_create_cart(request) # Get the current cart

            try:
                cart_item = CartItem.objects.get(cart=cart, product=product)
                cart_item.delete() 
                messages.success(request, f"{product.name} removed from your cart.")
            except CartItem.DoesNotExist:
                messages.error(request, "Product not found in your cart.")

            request.session['cart_count'] = sum(item.quantity for item in cart.items.all())
            
            # Recalculate total price for immediate update on the cart page
            new_total_price = sum(item.total_price for item in cart.items.all())

            return JsonResponse({'success': True, 'cart_count': request.session['cart_count'], 'new_total_price': new_total_price})

        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON.'}, status=400)
        except Exception as e:
            
            print(f"Error removing from cart: {e}")
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)

def checkout_success(request):
    return render(request, 'shop/checkout_success.html', {})

@login_required 
def checkout(request):
    cart = get_or_create_cart(request)
    cart_items = cart.items.all()
    total_price = sum(item.total_price for item in cart_items)

    if not cart_items:
        messages.error(request, "Your cart is empty. Please add items before checking out.")
        return redirect('view_cart')

    if request.method == 'POST':
        payment_id = request.POST.get('razorpay_payment_id')
        razorpay_order_id = request.POST.get('razorpay_order_id')
        razorpay_signature = request.POST.get('razorpay_signature')

        try:
            
            client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': razorpay_signature
            })
            
            cart_items.delete() 
            request.session['cart_count'] = 0 
            messages.success(request, "Your order has been placed successfully!")
            return redirect('checkout_success') 

        except Exception as e:
            messages.error(request, f"Payment verification failed: {e}. Please try again.")
            return redirect('checkout')

    amount_in_paisa = int(total_price * 100)  
    order_receipt = f"receipt_cart_{cart.id}_{request.user.id}_{int(datetime.datetime.now().timestamp())}"

    try:
        # Create Razorpay order
        razorpay_order = client.order.create({
            'amount': amount_in_paisa,
            'currency': 'INR', 
            'receipt': order_receipt,
            'payment_capture': '1'  
        })
        razorpay_order_id = razorpay_order['id']
    except Exception as e:
        messages.error(request, f"Error creating Razorpay order: {e}. Please try again.")
        return redirect('view_cart') 

    context = {
        'cart_items': cart_items,
        'total_price': total_price,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'razorpay_order_id': razorpay_order_id,
        'razorpay_amount': amount_in_paisa,
        'customer_name': request.user.username if request.user.is_authenticated else 'Guest',
        'customer_email': request.user.email if request.user.is_authenticated else '',
        'customer_phone': '9999999999', 
    }
    return render(request, 'shop/checkout.html', context)