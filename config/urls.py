"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf.urls.static import static
from django.urls import path
from config import settings
from books import views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('',  views.home, name='home'),
    path('about/', views.about, name='about'),
    path('profile/', views.profile, name='profile'),
    path('catalogue/', views.catalogue, name='catalogue'),
    path('books/<int:book_id>/', views.book_detail, name='book-detail'),
    path('orders/', views.orders, name='orders'),
    path('orders/history/', views.previous_orders, name='previous-orders'),
    path('orders/add/<int:book_id>/', views.add_to_order, name='add-to-order'),
    path('orders/submit/', views.submit_order, name='submit-order'),
    path('admin-panel/', views.admin_dashboard, name='admin-dashboard'),
    path('admin-panel/books/', views.admin_books, name='admin-books'),
    path('admin-panel/orders/', views.admin_orders, name='admin-orders'),
    path('register', views.register, name='register'),
    path('login', views.login_view, name='login'),
    path('logout', views.logout_view, name='logout'),
    path('check-session', views.check_session, name='check-session'),
    path('api/books/', views.books_api, name='books-api'),
    path('api/books/<int:book_id>/', views.book_detail_api, name='book-detail-api'),
]

if settings.DEBUG:
    from django.urls import include
    urlpatterns += [
        path('__reload__/', include('django_browser_reload.urls')),
    ]

# Serve media files in both development and production
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


