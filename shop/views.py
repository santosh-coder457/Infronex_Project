from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import json
from django.conf import settings
import razorpay
import datetime
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt #Razorpay webhook
from .models import Product, Cart, CartItem, Address, Order, OrderItem, Payment
from .forms import AddressForm 

#Razorpay client
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
client.set_app_details({"title": "Django E-commerce", "version": "1.0"})


def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        if request.session.session_key and not created:
            session_cart = Cart.objects.filter(session_key=request.session.session_key).exclude(user=request.user).first()
            if session_cart:
                #Mergecart items
                for item in session_cart.items.all():
                    cart_item, created_item = CartItem.objects.get_or_create(cart=cart, product=item.product)
                    if not created_item:
                        cart_item.quantity += item.quantity
                    else:
                        cart_item.quantity = item.quantity #overwrite quantity or merge as per your logic
                    cart_item.save()
                session_cart.delete()
                request.session.pop('cart_count', None) # Clear session cart count
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key)

    request.session['cart_count'] = sum(item.quantity for item in cart.items.all())
    return cart

def create_order_from_cart(cart, user, shipping_address, billing_address=None):
    if not cart.items.exists():
        return None, None 

    with transaction.atomic(): #order and payment creation
        order = Order.objects.create(
            user=user,
            total_amount=cart.total_price,
            shipping_address=shipping_address,
            billing_address=billing_address if billing_address else shipping_address, # Use shipping if billing not provided
            status='pending' #Initial status
        )

        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.product.price #Save price
            )
        
        payment = Payment.objects.create(
            user=user,
            order=order,                     # Create a pending payment
            amount=order.total_amount,
            status='pending' #payment status
        )
        return order, payment


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
            
            # Recalculate total price
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

def checkout_failed(request):
    return render(request, 'shop/checkout_failed.html', {}) # Ensure you create this template


@login_required
def checkout(request):
    cart = get_or_create_cart(request)
    cart_items = cart.items.all()
    total_price = sum(item.total_price for item in cart_items)

    if not cart_items:
        messages.error(request, "Your cart is empty. Please add items before checking out.")
        return redirect('view_cart')

    user_address = None
    try:
        user_address = request.user.addresses.get(is_default=True)
    except Address.DoesNotExist:
        user_address = request.user.addresses.first()

    address_form = AddressForm(instance=user_address) #initialize address_form for GET request

    order = None 
    payment = None

    if request.method == 'POST':
        address_form = AddressForm(request.POST, instance=user_address)
        if address_form.is_valid():
            address = address_form.save(commit=False)
            address.user = request.user
            if not request.user.addresses.exists():
                address.is_default = True
            address.save()
            messages.success(request, "Shipping address saved successfully! Please proceed to payment.")
            user_address = address #update user_address

            order, payment = create_order_from_cart(cart, request.user, user_address)
            
            if not order or not payment:
                messages.error(request, "Could not create order from cart. Please try again.")
                return redirect('view_cart') # Or render checkout with error

        else:
            messages.error(request, "Please correct the errors in your address details.")
    
    razorpay_order_id = None
    if user_address and order and payment: #address, order, and payment linked
        amount_in_paisa = int(total_price * 100)
        order_receipt = f"receipt_order_{order.id}_{request.user.id}_{int(datetime.datetime.now().timestamp())}"

        try:
            razorpay_order = client.order.create({
                'amount': amount_in_paisa,
                'currency': 'INR',
                'receipt': order_receipt,
                'payment_capture': '1'
            })
            razorpay_order_id = razorpay_order['id']
            
            payment.transaction_id = razorpay_order_id #initial link
            payment.save()

        except Exception as e:
            messages.error(request, f"Error creating Razorpay order: {e}. Please ensure your Razorpay keys are correct and try again.")
            if payment: #successfully created
                payment.status = 'failed'
                payment.save()
            razorpay_order_id = None
            order = None

    context = {
        'cart_items': cart_items,
        'total_price': total_price,
        'address_form': address_form,
        'user_address': user_address,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'razorpay_order_id': razorpay_order_id,
        'razorpay_amount': amount_in_paisa if user_address and order else 0,
        'customer_name': request.user.username if request.user.is_authenticated else 'Guest User',
        'customer_email': request.user.email if request.user.is_authenticated else '',
        'customer_phone': user_address.phone_number if user_address and user_address.phone_number else '9999999999',
    }
    return render(request, 'shop/checkout.html', context)


@csrf_exempt
@transaction.atomic 
def razorpay_callback(request):
    """
    Handles the callback from Razorpay after payment completion/failure.
    This view receives payment details from Razorpay via POST request.
    """
    if request.method == 'POST':
        try:
            payment_id = request.POST.get('razorpay_payment_id')
            razorpay_order_id = request.POST.get('razorpay_order_id')
            razorpay_signature = request.POST.get('razorpay_signature')
    
            payment = Payment.objects.select_for_update().get(transaction_id=razorpay_order_id)

            client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': razorpay_signature
            })

            payment.status = 'successful'
            payment.gateway_response = request.POST.dict() 
            payment.transaction_id = payment_id
            payment.save()

            order = payment.order
            if order:
                order.status = 'paid'
                order.save()
                
                cart = get_object_or_404(Cart, user=payment.user)
                cart.items.all().delete()
                request.session['cart_count'] = 0 

            messages.success(request, "Your payment was successful!")
            return redirect('checkout_success')

        except Payment.DoesNotExist:
            messages.error(request, "Payment record not found for verification.")
            return redirect('checkout_failed')
        except Exception as e:
            if 'payment' in locals(): 
                payment.status = 'failed'
                payment.gateway_response = request.POST.dict()
                payment.save()
            messages.error(request, f"Payment failed: {e}. Please try again or contact support.")
            return redirect('checkout_failed')
    
    messages.error(request, "Invalid payment callback received.")
    return redirect('checkout_failed')

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'shop/order_detail.html', {'order': order})