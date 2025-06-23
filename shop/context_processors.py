from .models import Cart

def cart_context(request):
    cart_count = 0
    cart_total = 0
    cart_items_list = []

    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            cart = None
    else:
        session_key = request.session.session_key
        if session_key:
            try:
                cart = Cart.objects.get(session_key=session_key)
            except Cart.DoesNotExist:
                cart = None
        else:
            cart = None

    if cart:
        cart_count = sum(item.quantity for item in cart.items.all())
        cart_total = cart.total_price
        cart_items_list = cart.items.all()

    return {
        'cart_count': cart_count,
        'request_cart_items': cart_items_list,
        'request_cart_total': cart_total,
    }