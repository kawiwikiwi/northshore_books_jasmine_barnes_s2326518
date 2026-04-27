import json
from decimal import Decimal, InvalidOperation
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import update_session_auth_hash
from django.utils import timezone
from .models import User, Book, Order, OrderItem

# Create your views here.
def home(request):
    featured_books = Book.objects.order_by('?')[:8]
    return render(request, 'index.html', {'featured_books': featured_books})


def about(request):
    return render(request, 'about.html')


@login_required
def profile(request):
    success = ''
    error = ''

    if request.method == 'POST':
        action = request.POST.get('action', 'details')

        if action == 'details':
            name = request.POST.get('name', '').strip()
            email = request.POST.get('email', '').strip()

            if not name or not email:
                error = 'Name and email are required.'
            elif User.objects.exclude(id=request.user.id).filter(email=email).exists():
                error = 'That email address is already in use.'
            else:
                request.user.name = name
                request.user.email = email
                request.user.save(update_fields=['name', 'email'])
                success = 'Profile details updated successfully.'

        elif action == 'image':
            profile_image = request.FILES.get('profile_image')

            if not profile_image:
                error = 'Please choose an image to upload.'
            else:
                request.user.profile_image = profile_image
                request.user.save(update_fields=['profile_image'])
                success = 'Profile picture uploaded successfully.'

        elif action == 'password':
            current_password = request.POST.get('current_password', '')
            new_password = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')

            if not current_password:
                error = 'Current password is required to change your password.'
            elif not request.user.check_password(current_password):
                error = 'Current password is incorrect.'
            elif not new_password or not confirm_password:
                error = 'Please enter and confirm a new password.'
            elif new_password != confirm_password:
                error = 'New passwords do not match.'
            elif len(new_password) < 8:
                error = 'New password must be at least 8 characters long.'
            else:
                request.user.set_password(new_password)
                request.user.save(update_fields=['password'])
                update_session_auth_hash(request, request.user)
                success = 'Password updated successfully.'

        else:
            error = 'Unknown profile action.'

    return render(
        request,
        'profile.html',
        {
            'success': success,
            'error': error,
        },
    )


def catalogue(request):
    query = request.GET.get('q', '').strip()
    author = request.GET.get('author', '').strip()

    books_qs = Book.objects.all()
    if query:
        books_qs = books_qs.filter(Q(title__icontains=query) | Q(author__icontains=query))
    if author:
        books_qs = books_qs.filter(author__icontains=author)

    paginator = Paginator(books_qs, 12)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(
        request,
        'catalogue.html',
        {
            'books': page_obj,
            'page_obj': page_obj,
            'q': query,
            'author': author,
        },
    )


def book_detail(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    return render(request, 'book_detail.html', {'book': book})


@login_required
def orders(request):
    draft_order = (
        Order.objects.filter(user=request.user, status=Order.STATUS_DRAFT)
        .prefetch_related('items__book')
        .first()
    )

    return render(
        request,
        'orders.html',
        {
            'draft_order': draft_order,
        },
    )


@login_required
def previous_orders(request):
    submitted_orders = Order.objects.filter(
        user=request.user,
        status=Order.STATUS_SUBMITTED,
    ).prefetch_related('items__book')

    return render(
        request,
        'previous_orders.html',
        {
            'submitted_orders': submitted_orders,
        },
    )


@login_required
def add_to_order(request, book_id):
    if request.method != 'POST':
        return HttpResponse('Method not allowed', status=405)

    book = get_object_or_404(Book, id=book_id)
    order, _ = Order.objects.get_or_create(
        user=request.user,
        status=Order.STATUS_DRAFT,
    )

    item, created = OrderItem.objects.get_or_create(
        order=order,
        book=book,
        defaults={'quantity': 1, 'unit_price': book.price},
    )

    if not created:
        item.quantity += 1
        item.save(update_fields=['quantity'])

    next_url = request.POST.get('next') or 'catalogue'
    return redirect(next_url)


@login_required
def submit_order(request):
    if request.method != 'POST':
        return HttpResponse('Method not allowed', status=405)

    draft_order = (
        Order.objects.filter(user=request.user, status=Order.STATUS_DRAFT)
        .prefetch_related('items')
        .first()
    )
    if not draft_order or not draft_order.items.exists():
        return redirect('orders')

    draft_order.status = Order.STATUS_SUBMITTED
    draft_order.submitted_at = timezone.now()
    draft_order.save(update_fields=['status', 'submitted_at'])
    return redirect('previous-orders')


@staff_member_required(login_url='login')
def admin_dashboard(request):
    return render(request, 'admin_dashboard.html')


@staff_member_required(login_url='login')
def admin_books(request):
    error = ''

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'delete':
            book = get_object_or_404(Book, id=request.POST.get('book_id'))
            book.delete()
            return redirect('admin-books')

        title = request.POST.get('title', '').strip()
        author = request.POST.get('author', '').strip()
        price_raw = request.POST.get('price', '').strip()
        description = request.POST.get('description', '').strip()
        cover_image = request.POST.get('cover_image', '').strip()

        if not title or not author or not price_raw or not description:
            error = 'Title, author, price, and description are required.'
        else:
            try:
                price = Decimal(price_raw)
            except (InvalidOperation, TypeError):
                error = 'Price must be a valid number.'
            else:
                if price < 0:
                    error = 'Price must be non-negative.'
                elif action == 'add':
                    Book.objects.create(
                        title=title,
                        author=author,
                        price=price,
                        description=description,
                        cover_image=cover_image,
                    )
                    return redirect('admin-books')
                elif action == 'update':
                    book = get_object_or_404(Book, id=request.POST.get('book_id'))
                    book.title = title
                    book.author = author
                    book.price = price
                    book.description = description
                    book.cover_image = cover_image
                    book.save()
                    return redirect('admin-books')

    query = request.GET.get('q', '').strip()
    books_qs = Book.objects.all()
    if query:
        books_qs = books_qs.filter(Q(title__icontains=query) | Q(author__icontains=query))

    edit_book = None
    edit_id = request.GET.get('edit')
    if edit_id:
        edit_book = get_object_or_404(Book, id=edit_id)

    return render(
        request,
        'admin_books.html',
        {
            'books': books_qs,
            'query': query,
            'edit_book': edit_book,
            'error': error,
        },
    )


@staff_member_required(login_url='login')
def admin_orders(request):
    status_filter = request.GET.get('status', Order.STATUS_SUBMITTED)
    query = request.GET.get('q', '').strip()
    orders_qs = Order.objects.select_related('user').prefetch_related('items__book')

    if status_filter in [Order.STATUS_DRAFT, Order.STATUS_SUBMITTED]:
        orders_qs = orders_qs.filter(status=status_filter)

    if query:
        orders_qs = orders_qs.filter(
            Q(user__email__icontains=query)
            | Q(items__book__title__icontains=query)
        ).distinct()

    return render(
        request,
        'admin_orders.html',
        {
            'orders': orders_qs,
            'status_filter': status_filter,
            'query': query,
        },
    )

@csrf_exempt
def register(request):
    if request.method == 'GET':
        return render(request, 'register.html')
    
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    # Validate required fields
    if not data.get('email') or not data.get('name') or not data.get('password'):
        return JsonResponse({'error': 'Email, name, and password are required'}, status=400)
    
    # Check if user exists
    if User.objects.filter(email=data['email']).exists():
        return JsonResponse({'error': 'Email already registered'}, status=409)
    
    # Validate password length
    if len(data['password']) < 8:
        return JsonResponse({'error': 'Password must be at least 8 characters long'}, status=400)
    
    try:
        User.objects.create_user(
            email=data['email'], 
            name=data['name'], 
            password=data['password']
        )
        return JsonResponse({'message': 'User registered successfully'}, status=201)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def login_view(request):
    if request.method == 'GET':
        return render(request, 'login.html')
    
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    if not data.get('email') or not data.get('password'):
        return JsonResponse({'error': 'Email and password are required'}, status=400)
    
    user = authenticate(request, email=data['email'], password=data['password'])
    if user:
        login(request, user)
        return JsonResponse({'message': 'Login successful'}, status=200)
    return JsonResponse({'error': 'Invalid credentials'}, status=401)

def logout_view(request):
    if request.method not in ['GET', 'POST']:
        return HttpResponse('Method not allowed', status=405)

    logout(request)
    return render(request, 'logout.html')

def check_session(request):
    if request.user.is_authenticated:
        return JsonResponse({'logged_in': True, 'userName': request.user.name})
    return JsonResponse({'logged_in': False})


def _book_to_dict(book):
    return {
        'id': book.id,
        'title': book.title,
        'author': book.author,
        'price': str(book.price),
        'description': book.description,
        'cover_image': book.cover_image,
    }


def _parse_json_body(request):
    try:
        return json.loads(request.body or '{}'), None
    except json.JSONDecodeError:
        return None, JsonResponse({'error': 'Invalid JSON payload'}, status=400)


def _ensure_admin_user(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    if not request.user.is_staff:
        return JsonResponse({'error': 'Admin access required'}, status=403)
    return None


def _validate_book_payload(data, partial=False):
    required_fields = ['title', 'author', 'price', 'description']
    if not partial:
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return f"Missing required fields: {', '.join(missing_fields)}"

    if 'price' in data:
        try:
            price = Decimal(str(data['price']))
        except (InvalidOperation, TypeError):
            return 'Price must be a valid number'
        if price < 0:
            return 'Price must be non-negative'

    return None


@csrf_exempt
def books_api(request):
    if request.method == 'GET':
        query = request.GET.get('q', '').strip()
        author = request.GET.get('author', '').strip()

        books_qs = Book.objects.all()
        if query:
            books_qs = books_qs.filter(Q(title__icontains=query) | Q(author__icontains=query))
        if author:
            books_qs = books_qs.filter(author__icontains=author)

        try:
            page_size = int(request.GET.get('page_size', 10))
        except ValueError:
            return JsonResponse({'error': 'page_size must be an integer'}, status=400)

        if page_size < 1 or page_size > 100:
            return JsonResponse({'error': 'page_size must be between 1 and 100'}, status=400)

        paginator = Paginator(books_qs, page_size)
        page_obj = paginator.get_page(request.GET.get('page', 1))

        return JsonResponse(
            {
                'count': paginator.count,
                'num_pages': paginator.num_pages,
                'current_page': page_obj.number,
                'results': [_book_to_dict(book) for book in page_obj.object_list],
            },
            status=200,
        )

    if request.method == 'POST':
        admin_error = _ensure_admin_user(request)
        if admin_error:
            return admin_error

        data, parse_error = _parse_json_body(request)
        if parse_error:
            return parse_error

        validation_error = _validate_book_payload(data)
        if validation_error:
            return JsonResponse({'error': validation_error}, status=400)

        book = Book.objects.create(
            title=data['title'],
            author=data['author'],
            price=Decimal(str(data['price'])),
            description=data['description'],
            cover_image=data.get('cover_image', ''),
        )
        return JsonResponse(_book_to_dict(book), status=201)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def book_detail_api(request, book_id):
    book = get_object_or_404(Book, id=book_id)

    if request.method == 'GET':
        return JsonResponse(_book_to_dict(book))

    if request.method in ['PUT', 'PATCH']:
        admin_error = _ensure_admin_user(request)
        if admin_error:
            return admin_error

        data, parse_error = _parse_json_body(request)
        if parse_error:
            return parse_error

        validation_error = _validate_book_payload(data, partial=(request.method == 'PATCH'))
        if validation_error:
            return JsonResponse({'error': validation_error}, status=400)

        if 'title' in data:
            book.title = data['title']
        if 'author' in data:
            book.author = data['author']
        if 'price' in data:
            book.price = Decimal(str(data['price']))
        if 'description' in data:
            book.description = data['description']
        if 'cover_image' in data:
            book.cover_image = data['cover_image']
        book.save()

        return JsonResponse(_book_to_dict(book))

    if request.method == 'DELETE':
        admin_error = _ensure_admin_user(request)
        if admin_error:
            return admin_error

        book.delete()
        return JsonResponse({}, status=204)

    return JsonResponse({'error': 'Method not allowed'}, status=405)