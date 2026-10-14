import unittest
from app import app
from database import init_db, get_db_connection

class PaintingPlatformTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test_secret_key'
        self.client = app.test_client()
        conn = get_db_connection()
        conn.execute('DROP TABLE IF EXISTS order_items')
        conn.execute('DROP TABLE IF EXISTS orders')
        conn.execute('DROP TABLE IF EXISTS paintings')
        conn.execute('DROP TABLE IF EXISTS artists')
        conn.commit()
        conn.close()
        init_db()

    def test_homepage_loads(self):
        """Test gallery homepage with search and painting cards."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Artisan Canvas', response.data)
        self.assertIn(b'Whispering Pines', response.data)
        self.assertIn(b'Elena Rostova', response.data)

    def test_painting_detail(self):
        """Test painting detail page with specs and artist info."""
        response = self.client.get('/painting/1')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Whispering Pines in Morning Mist', response.data)
        self.assertIn(b'Elena Rostova', response.data)
        self.assertIn(b'Oil on Linen', response.data)
        self.assertIn(b'Add to Collection Cart', response.data)

    def test_cart_and_checkout_flow(self):
        """Test adding a painting to cart, checking out, and verifying database status."""
        # 1. Add to cart
        res_add = self.client.post('/cart/add/1', headers={'X-Requested-With': 'XMLHttpRequest'})
        self.assertEqual(res_add.status_code, 200)
        data = res_add.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['cart_count'], 1)

        # 2. View cart
        res_cart = self.client.get('/cart')
        self.assertEqual(res_cart.status_code, 200)
        self.assertIn(b'Whispering Pines in Morning Mist', res_cart.data)
        self.assertIn(b'Acquisition Summary', res_cart.data)

        # 3. Complete checkout
        res_checkout = self.client.post('/checkout', data={
            'buyer_name': 'Vincent Van Test',
            'buyer_email': 'vincent@tester.com',
            'address': '123 Studio Way, Amsterdam, Netherlands',
            'payment_method': 'Credit Card (Simulated Secure)'
        }, follow_redirects=True)
        self.assertEqual(res_checkout.status_code, 200)
        self.assertIn(b'Congratulations on Your Art Acquisition', res_checkout.data)
        self.assertIn(b'Vincent Van Test', res_checkout.data)

        # 4. Verify in SQL database that painting status is now 'Sold'
        conn = get_db_connection()
        p = conn.execute('SELECT status FROM paintings WHERE id = 1').fetchone()
        self.assertEqual(p['status'], 'Sold')

        # 5. Verify the order item exists in SQL database
        item = conn.execute('SELECT * FROM order_items WHERE painting_id = 1').fetchone()
        self.assertIsNotNone(item)
        self.assertEqual(item['price'], 1250.00)
        conn.close()

    def test_artist_dashboard_and_sales_details(self):
        """Test the artist dashboard showing sales details and paintings."""
        # Elena Rostova is artist_id 1
        with self.client.session_transaction() as sess:
            sess['active_artist_id'] = 1

        response = self.client.get('/artist/dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Artist Studio & Sales Portal', response.data)
        self.assertIn(b'Elena Rostova', response.data)
        self.assertIn(b'Painting Sales Details & Transaction History', response.data)
        self.assertIn(b'Total Sales Revenue', response.data)

    def test_add_new_painting(self):
        """Test painter uploading/adding a new painting."""
        res = self.client.post('/artist/add-painting', data={
            'title': 'Sage Whisper at Twilight',
            'artist_id': 1,
            'medium': 'Oil on Stretched Linen',
            'dimensions': '30" x 40"',
            'year': 2026,
            'price': 1850.00,
            'image_url': 'https://images.unsplash.com/photo-1579783900882-c0d3dad7b119',
            'description': 'A serene landscape in sage green and deep olive oil layers.'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Verify painting in SQL database
        conn = get_db_connection()
        p = conn.execute('SELECT * FROM paintings WHERE title = "Sage Whisper at Twilight"').fetchone()
        self.assertIsNotNone(p)
        self.assertEqual(p['price'], 1850.00)
        self.assertEqual(p['status'], 'Available')
        conn.close()

if __name__ == '__main__':
    unittest.main()
