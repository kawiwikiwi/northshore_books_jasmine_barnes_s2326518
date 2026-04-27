from django.contrib import admin
from .models import Book, Order, OrderItem

# Register your models here.


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
	list_display = ('title', 'author', 'price', 'created_at')
	search_fields = ('title', 'author')


class OrderItemInline(admin.TabularInline):
	model = OrderItem
	extra = 0
	readonly_fields = ('book', 'quantity', 'unit_price')
	can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
	list_display = ('id', 'user', 'status', 'created_at', 'submitted_at')
	list_filter = ('status', 'created_at')
	search_fields = ('user__email',)
	inlines = [OrderItemInline]
