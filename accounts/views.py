from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from .forms import SignUpForm, LoginForm
from shop.models import Cart, CartItem  # Import Cart model


def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
           
            session_key = request.session.session_key
            if session_key:
                try:
                    anon_cart = Cart.objects.get(session_key=session_key, user__isnull=True)
                    anon_cart.user = user
                    anon_cart.session_key = None 
                    anon_cart.save()
                    messages.success(request, f"Welcome, {user.username}! Your cart has been loaded.")
                except Cart.DoesNotExist:
                    messages.success(request, f"Welcome, {user.username}! You can now start shopping.")
            else:
                messages.success(request, f"Welcome, {user.username}! You can now start shopping.")

            login(request, user) 
            return redirect('product_list') 
    else:
        form = SignUpForm()
    return render(request, 'accounts/signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                
                session_key = request.session.session_key
                if session_key:
                    try:
                        anon_cart = Cart.objects.get(session_key=session_key, user__isnull=True)
                        user_cart, created_user_cart = Cart.objects.get_or_create(user=user)

                        
                        if not created_user_cart: 
                            for item in anon_cart.items.all():
                                user_cart_item, created_item = CartItem.objects.get_or_create(cart=user_cart, product=item.product)
                                if not created_item:
                                    user_cart_item.quantity += item.quantity
                                else:
                                    user_cart_item.quantity = item.quantity
                                user_cart_item.save()
                            anon_cart.delete() 

                        else: 
                            anon_cart.user = user
                            anon_cart.session_key = None
                            anon_cart.save()
                        messages.success(request, f"Welcome back, {user.username}! Your cart has been loaded.")
                    except Cart.DoesNotExist:
                        messages.success(request, f"Welcome back, {user.username}!")
                else:
                    messages.success(request, f"Welcome back, {user.username}!")
                return redirect('product_list')
            else:
                messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('product_list')