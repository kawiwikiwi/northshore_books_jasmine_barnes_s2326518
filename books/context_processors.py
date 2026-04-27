from decimal import Decimal

from .models import Order


def cart_dropdown(request):
    if not request.user.is_authenticated:
        return {
            'cart_item_count': 0,
            'cart_subtotal': Decimal('0.00'),
            'cart_preview_items': [],
            'cart_has_items': False,
        }

    draft_order = (
        Order.objects.filter(user=request.user, status=Order.STATUS_DRAFT)
        .prefetch_related('items__book')
        .first()
    )

    if not draft_order:
        return {
            'cart_item_count': 0,
            'cart_subtotal': Decimal('0.00'),
            'cart_preview_items': [],
            'cart_has_items': False,
        }

    items = list(draft_order.items.all())
    cart_item_count = sum(item.quantity for item in items)
    cart_subtotal = sum((item.line_total for item in items), Decimal('0.00'))

    cart_preview_items = [
        {
            'title': item.book.title,
            'quantity': item.quantity,
            'line_total': item.line_total,
        }
        for item in items[:3]
    ]

    return {
        'cart_item_count': cart_item_count,
        'cart_subtotal': cart_subtotal,
        'cart_preview_items': cart_preview_items,
        'cart_has_items': cart_item_count > 0,
    }
