from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Book, User, Order, OrderItem

# Create your tests here.


class BookCatalogueTests(TestCase):
	def setUp(self):
		self.book = Book.objects.create(
			title='Clean Code',
			author='Robert C. Martin',
			price='29.99',
			description='A handbook of agile software craftsmanship.',
			cover_image='https://example.com/clean-code.jpg',
		)
		self.admin_user = User.objects.create_superuser(
			email='admin@example.com',
			name='Admin User',
			password='AdminPass123!',
		)
		self.second_book = Book.objects.create(
			title='Refactoring',
			author='Martin Fowler',
			price='39.99',
			description='Improving the design of existing code.',
			cover_image='https://example.com/refactoring.jpg',
		)

	def test_catalogue_page_is_public(self):
		response = self.client.get(reverse('catalogue'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Clean Code')

	def test_home_page_is_public(self):
		response = self.client.get(reverse('home'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Welcome to Northshore Books')
		self.assertContains(response, 'Discover Something New')

	def test_book_detail_page_is_public(self):
		response = self.client.get(reverse('book-detail', args=[self.book.id]))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Robert C. Martin')

	def test_books_api_get_list_is_public(self):
		response = self.client.get(reverse('books-api'))
		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertEqual(payload['count'], 2)
		self.assertEqual(len(payload['results']), 2)

	def test_books_api_supports_search_filter(self):
		response = self.client.get(reverse('books-api'), {'q': 'Clean'})
		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertEqual(payload['count'], 1)
		self.assertEqual(payload['results'][0]['title'], 'Clean Code')

	def test_books_api_supports_pagination(self):
		response = self.client.get(reverse('books-api'), {'page': 1, 'page_size': 1})
		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertEqual(payload['num_pages'], 2)
		self.assertEqual(len(payload['results']), 1)

	def test_books_api_post_requires_admin(self):
		payload = {
			'title': 'Domain-Driven Design',
			'author': 'Eric Evans',
			'price': '34.99',
			'description': 'Tackling complexity in software design.',
			'cover_image': 'https://example.com/ddd.jpg',
		}
		response = self.client.post(
			reverse('books-api'),
			data=payload,
			content_type='application/json',
		)
		self.assertEqual(response.status_code, 401)

	def test_books_api_post_works_for_admin(self):
		self.client.force_login(self.admin_user)
		payload = {
			'title': 'Refactoring',
			'author': 'Martin Fowler',
			'price': '39.99',
			'description': 'Improving the design of existing code.',
			'cover_image': 'https://example.com/refactoring.jpg',
		}
		response = self.client.post(
			reverse('books-api'),
			data=payload,
			content_type='application/json',
		)
		self.assertEqual(response.status_code, 201)

	def test_books_api_patch_works_for_admin(self):
		self.client.force_login(self.admin_user)
		payload = {'price': '24.99'}
		response = self.client.patch(
			reverse('book-detail-api', args=[self.book.id]),
			data=payload,
			content_type='application/json',
		)
		self.assertEqual(response.status_code, 200)
		self.book.refresh_from_db()
		self.assertEqual(str(self.book.price), '24.99')

	def test_books_api_delete_works_for_admin(self):
		self.client.force_login(self.admin_user)
		response = self.client.delete(reverse('book-detail-api', args=[self.book.id]))
		self.assertEqual(response.status_code, 204)
		self.assertFalse(Book.objects.filter(id=self.book.id).exists())


class OrderManagementTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(
			email='reader@example.com',
			name='Reader',
			password='ReaderPass123!',
		)
		self.book = Book.objects.create(
			title='The Pragmatic Programmer',
			author='Andrew Hunt',
			price='25.00',
			description='A practical guide to programming craftsmanship.',
			cover_image='https://example.com/pragmatic.jpg',
		)

	def test_add_to_order_requires_login(self):
		response = self.client.post(reverse('add-to-order', args=[self.book.id]))
		self.assertEqual(response.status_code, 302)
		self.assertIn(reverse('login'), response.url)

	def test_logged_in_user_can_add_and_submit_order(self):
		self.client.force_login(self.user)

		add_response = self.client.post(reverse('add-to-order', args=[self.book.id]))
		self.assertEqual(add_response.status_code, 302)

		order = Order.objects.get(user=self.user, status=Order.STATUS_DRAFT)
		self.assertEqual(order.items.count(), 1)
		self.assertEqual(order.items.first().quantity, 1)

		submit_response = self.client.post(reverse('submit-order'))
		self.assertEqual(submit_response.status_code, 302)

		order.refresh_from_db()
		self.assertEqual(order.status, Order.STATUS_SUBMITTED)
		self.assertIsNotNone(order.submitted_at)

	def test_user_can_view_previous_orders_read_only(self):
		self.client.force_login(self.user)
		self.client.post(reverse('add-to-order', args=[self.book.id]))
		self.client.post(reverse('submit-order'))

		response = self.client.get(reverse('previous-orders'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Previous Orders')
		self.assertContains(response, 'The Pragmatic Programmer')

	def test_user_can_view_current_order_page(self):
		self.client.force_login(self.user)
		response = self.client.get(reverse('orders'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Current Order')

	def test_cart_dropdown_shows_live_cart_data(self):
		self.client.force_login(self.user)
		self.client.post(reverse('add-to-order', args=[self.book.id]))
		self.client.post(reverse('add-to-order', args=[self.book.id]))

		response = self.client.get(reverse('catalogue'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, '2 items')
		self.assertContains(response, 'Subtotal: £50.00')
		self.assertContains(response, 'View Current Order')

	def test_user_can_view_profile_page(self):
		self.client.force_login(self.user)
		response = self.client.get(reverse('profile'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'My Profile')

	def test_user_can_update_profile_details_and_password(self):
		self.client.force_login(self.user)
		response = self.client.post(
			reverse('profile'),
			data={
				'action': 'details',
				'name': 'Updated Reader',
				'email': 'updated-reader@example.com',
			},
		)
		self.assertEqual(response.status_code, 200)
		self.user.refresh_from_db()
		self.assertEqual(self.user.name, 'Updated Reader')
		self.assertEqual(self.user.email, 'updated-reader@example.com')

		password_response = self.client.post(
			reverse('profile'),
			data={
				'action': 'password',
				'current_password': 'ReaderPass123!',
				'new_password': 'NewReaderPass123!',
				'confirm_password': 'NewReaderPass123!',
			},
		)
		self.assertEqual(password_response.status_code, 200)
		self.user.refresh_from_db()
		self.assertTrue(self.client.login(email='updated-reader@example.com', password='NewReaderPass123!'))

	def test_user_can_upload_profile_image(self):
		self.client.force_login(self.user)
		image = SimpleUploadedFile(
			'avatar.png',
			b'fake image content',
			content_type='image/png',
		)

		response = self.client.post(
			reverse('profile'),
			data={
				'action': 'image',
				'name': self.user.name,
				'email': self.user.email,
				'profile_image': image,
			},
		)
		self.assertEqual(response.status_code, 200)
		self.user.refresh_from_db()
		self.assertTrue(self.user.profile_image.name.startswith('profile_images/'))


class AdminFunctionalityTests(TestCase):
	def setUp(self):
		self.admin_user = User.objects.create_superuser(
			email='admin2@example.com',
			name='Admin Two',
			password='AdminPass123!',
		)
		self.regular_user = User.objects.create_user(
			email='reader2@example.com',
			name='Reader Two',
			password='ReaderPass123!',
		)
		self.book = Book.objects.create(
			title='Design Patterns',
			author='Erich Gamma',
			price='30.00',
			description='Classic software design patterns.',
			cover_image='https://example.com/design-patterns.jpg',
		)

	def test_admin_pages_require_staff_user(self):
		self.client.force_login(self.regular_user)
		response = self.client.get(reverse('admin-books'))
		self.assertEqual(response.status_code, 302)
		response = self.client.get(reverse('admin-dashboard'))
		self.assertEqual(response.status_code, 302)

	def test_admin_can_view_dashboard(self):
		self.client.force_login(self.admin_user)
		response = self.client.get(reverse('admin-dashboard'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Admin Dashboard')
		self.assertContains(response, 'Manage Books')
		self.assertContains(response, 'View Orders')

	def test_admin_can_add_update_delete_book(self):
		self.client.force_login(self.admin_user)

		add_response = self.client.post(
			reverse('admin-books'),
			data={
				'action': 'add',
				'title': 'DDD',
				'author': 'Eric Evans',
				'price': '34.99',
				'description': 'Domain-driven design guide.',
				'cover_image': 'https://example.com/ddd.jpg',
			},
		)
		self.assertEqual(add_response.status_code, 302)
		created = Book.objects.get(title='DDD')

		update_response = self.client.post(
			reverse('admin-books'),
			data={
				'action': 'update',
				'book_id': created.id,
				'title': 'Domain-Driven Design',
				'author': 'Eric Evans',
				'price': '35.99',
				'description': 'Updated description.',
				'cover_image': 'https://example.com/ddd-updated.jpg',
			},
		)
		self.assertEqual(update_response.status_code, 302)
		created.refresh_from_db()
		self.assertEqual(created.title, 'Domain-Driven Design')
		self.assertEqual(str(created.price), '35.99')

		delete_response = self.client.post(
			reverse('admin-books'),
			data={'action': 'delete', 'book_id': created.id},
		)
		self.assertEqual(delete_response.status_code, 302)
		self.assertFalse(Book.objects.filter(id=created.id).exists())

	def test_admin_can_view_customer_orders(self):
		order = Order.objects.create(
			user=self.regular_user,
			status=Order.STATUS_SUBMITTED,
		)
		OrderItem.objects.create(
			order=order,
			book=self.book,
			quantity=2,
			unit_price='30.00',
		)

		self.client.force_login(self.admin_user)
		response = self.client.get(reverse('admin-orders'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, self.regular_user.email)
		self.assertContains(response, 'Design Patterns')

	def test_admin_can_search_customer_orders(self):
		matching_order = Order.objects.create(
			user=self.regular_user,
			status=Order.STATUS_SUBMITTED,
		)
		OrderItem.objects.create(
			order=matching_order,
			book=self.book,
			quantity=1,
			unit_price='30.00',
		)

		other_user = User.objects.create_user(
			email='other@example.com',
			name='Other User',
			password='OtherPass123!',
		)
		other_book = Book.objects.create(
			title='Clean Architecture',
			author='Robert C. Martin',
			price='28.00',
			description='Software architecture guide.',
			cover_image='https://example.com/clean-architecture.jpg',
		)
		other_order = Order.objects.create(
			user=other_user,
			status=Order.STATUS_SUBMITTED,
		)
		OrderItem.objects.create(
			order=other_order,
			book=other_book,
			quantity=1,
			unit_price='28.00',
		)

		self.client.force_login(self.admin_user)
		response = self.client.get(reverse('admin-orders'), {'q': 'Design Patterns', 'status': 'submitted'})
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Design Patterns')
		self.assertNotContains(response, 'Clean Architecture')
