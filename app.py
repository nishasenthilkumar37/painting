import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from database import get_db_connection, init_db

# Determine root directory accurately
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(BASE_DIR) == 'api':
    ROOT_DIR = os.path.dirname(BASE_DIR)
else:
    ROOT_DIR = BASE_DIR

TEMPLATE_DIR = os.path.join(ROOT_DIR, 'templates')
STATIC_DIR = os.path.join(ROOT_DIR, 'static')

app = Flask(
    __name__,
    template_folder=TEMPLATE_DIR,
    static_folder=STATIC_DIR,
    static_url_path='/static'
)
app.secret_key = 'artisan_gallery_secret_key_sage_olive_2026'

# WSGI Middleware to fix Vercel /api/index prefix in PATH_INFO
class VercelPrefixMiddleware(object):
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        matched = environ.get('HTTP_X_MATCHED_PATH')
        if matched:
            environ['PATH_INFO'] = matched
        else:
            path = environ.get('PATH_INFO', '')
            if path.startswith('/api/index'):
                environ['PATH_INFO'] = path[len('/api/index'):] or '/'
            elif path.startswith('/api'):
                environ['PATH_INFO'] = path[len('/api'):] or '/'
        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelPrefixMiddleware(app.wsgi_app)

@app.route('/static/<path:filename>')
def custom_static(filename):
    return send_from_directory(STATIC_DIR, filename)

# Configure Upload Folder safely (support serverless /tmp)
IS_SERVERLESS = bool(os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'))
if IS_SERVERLESS:
    UPLOAD_FOLDER = '/tmp/uploads'
else:
    UPLOAD_FOLDER = os.path.join(STATIC_DIR, 'uploads')

try:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
except Exception:
    pass

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.context_processor
def inject_cart_info():
    """Make cart items count and active artist accessible in all templates."""
    cart = session.get('cart', [])
    active_artist_id = session.get('active_artist_id', 1)
    
    artists = []
    active_artist = None
    try:
        conn = get_db_connection()
        artists = conn.execute('SELECT id, name FROM artists ORDER BY name ASC').fetchall()
        active_artist = conn.execute('SELECT * FROM artists WHERE id = ?', (active_artist_id,)).fetchone()
        conn.close()
    except Exception as e:
        print(f"Context processor warning: {e}")

    return {
        'cart_count': len(cart),
        'all_artists_nav': artists,
        'active_artist': active_artist
    }

# ==========================================
# MARKETPLACE / GALLERY ROUTES
# ==========================================

@app.route('/')
def index():
    query_search = request.args.get('q', '').strip()
    filter_medium = request.args.get('medium', '').strip()
    filter_artist = request.args.get('artist', '').strip()
    filter_status = request.args.get('status', '').strip()
    sort_by = request.args.get('sort', 'newest')

    conn = get_db_connection()

    sql = '''
        SELECT p.*, a.name AS artist_name, a.location AS artist_location, a.avatar_url AS artist_avatar
        FROM paintings p
        JOIN artists a ON p.artist_id = a.id
        WHERE 1=1
    '''
    params = []

    if query_search:
        sql += ' AND (p.title LIKE ? OR p.description LIKE ? OR a.name LIKE ?)'
        wildcard = f'%{query_search}%'
        params.extend([wildcard, wildcard, wildcard])

    if filter_medium:
        sql += ' AND p.medium LIKE ?'
        params.append(f'%{filter_medium}%')

    if filter_artist:
        sql += ' AND p.artist_id = ?'
        params.append(filter_artist)

    if filter_status:
        sql += ' AND p.status = ?'
        params.append(filter_status)

    if sort_by == 'price_low':
        sql += ' ORDER BY p.price ASC'
    elif sort_by == 'price_high':
        sql += ' ORDER BY p.price DESC'
    elif sort_by == 'title':
        sql += ' ORDER BY p.title ASC'
    else:
        sql += ' ORDER BY p.created_at DESC'

    paintings = conn.execute(sql, params).fetchall()

    # Get media list for filter dropdown
    media_rows = conn.execute('SELECT DISTINCT medium FROM paintings').fetchall()
    all_media = [r['medium'] for r in media_rows]

    # Featured paintings
    featured_paintings = conn.execute('''
        SELECT p.*, a.name AS artist_name 
        FROM paintings p 
        JOIN artists a ON p.artist_id = a.id 
        WHERE p.featured = 1 AND p.status = 'Available'
        LIMIT 3
    ''').fetchall()

    artists = conn.execute('SELECT id, name FROM artists ORDER BY name ASC').fetchall()
    conn.close()

    return render_template(
        'index.html',
        paintings=paintings,
        featured_paintings=featured_paintings,
        all_media=all_media,
        artists=artists,
        query_search=query_search,
        filter_medium=filter_medium,
        filter_artist=filter_artist,
        filter_status=filter_status,
        sort_by=sort_by
    )

@app.route('/painting/<int:painting_id>')
def painting_detail(painting_id):
    conn = get_db_connection()
    painting = conn.execute('''
        SELECT p.*, a.name AS artist_name, a.bio AS artist_bio, a.location AS artist_location, 
               a.avatar_url AS artist_avatar, a.email AS artist_email, a.id AS artist_id
        FROM paintings p
        JOIN artists a ON p.artist_id = a.id
        WHERE p.id = ?
    ''', (painting_id,)).fetchone()

    if not painting:
        conn.close()
        flash('Artwork not found.', 'error')
        return redirect(url_for('index'))

    # More paintings by this artist
    related = conn.execute('''
        SELECT * FROM paintings 
        WHERE artist_id = ? AND id != ?
        ORDER BY created_at DESC LIMIT 3
    ''', (painting['artist_id'], painting_id)).fetchall()

    conn.close()

    in_cart = painting_id in session.get('cart', [])

    return render_template('painting_detail.html', painting=painting, related=related, in_cart=in_cart)

# ==========================================
# SHOPPING CART & CHECKOUT
# ==========================================

@app.route('/cart')
def cart():
    cart_ids = session.get('cart', [])
    paintings = []
    total = 0.0

    if cart_ids:
        conn = get_db_connection()
        placeholders = ','.join('?' for _ in cart_ids)
        paintings = conn.execute(f'''
            SELECT p.*, a.name AS artist_name 
            FROM paintings p
            JOIN artists a ON p.artist_id = a.id
            WHERE p.id IN ({placeholders})
        ''', cart_ids).fetchall()
        conn.close()

        total = sum(p['price'] for p in paintings)

    return render_template('cart.html', paintings=paintings, subtotal=total)

@app.route('/cart/add/<int:painting_id>', methods=['POST', 'GET'])
def add_to_cart(painting_id):
    cart = session.get('cart', [])
    
    conn = get_db_connection()
    painting = conn.execute('SELECT * FROM paintings WHERE id = ?', (painting_id,)).fetchone()
    conn.close()

    if not painting:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Artwork not found.'}), 404
        flash('Artwork not found.', 'error')
        return redirect(url_for('index'))

    if painting['status'] == 'Sold':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'This original painting has already been sold.'}), 400
        flash('This original piece has already been sold.', 'warning')
        return redirect(url_for('painting_detail', painting_id=painting_id))

    if painting_id not in cart:
        cart.append(painting_id)
        session['cart'] = cart
        message = f'"{painting["title"]}" added to your collection cart!'
        added = True
    else:
        message = f'"{painting["title"]}" is already in your cart.'
        added = False

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'added': added,
            'cart_count': len(cart),
            'message': message,
            'title': painting['title']
        })

    flash(message, 'success' if added else 'info')
    return redirect(request.referrer or url_for('cart'))

@app.route('/cart/remove/<int:painting_id>', methods=['POST', 'GET'])
def remove_from_cart(painting_id):
    cart = session.get('cart', [])
    if painting_id in cart:
        cart.remove(painting_id)
        session['cart'] = cart
        flash('Item removed from cart.', 'info')

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'cart_count': len(cart)})

    return redirect(url_for('cart'))

@app.route('/cart/clear')
def clear_cart():
    session['cart'] = []
    flash('Cart emptied.', 'info')
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['POST'])
def checkout():
    cart_ids = session.get('cart', [])
    if not cart_ids:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('cart'))

    buyer_name = request.form.get('buyer_name', '').strip()
    buyer_email = request.form.get('buyer_email', '').strip()
    address = request.form.get('address', '').strip()
    payment_method = request.form.get('payment_method', 'Card (Simulated Secure)')

    if not buyer_name or not buyer_email or not address:
        flash('Please fill in all buyer shipping details.', 'error')
        return redirect(url_for('cart'))

    conn = get_db_connection()
    cursor = conn.cursor()

    placeholders = ','.join('?' for _ in cart_ids)
    paintings = cursor.execute(f'''
        SELECT * FROM paintings WHERE id IN ({placeholders})
    ''', cart_ids).fetchall()

    sold_items = [p['title'] for p in paintings if p['status'] == 'Sold']
    if sold_items:
        conn.close()
        flash(f'One or more paintings were just sold: {", ".join(sold_items)}. Please review your cart.', 'error')
        return redirect(url_for('cart'))

    total_amount = sum(p['price'] for p in paintings)

    cursor.execute('''
        INSERT INTO orders (buyer_name, buyer_email, shipping_address, total_amount, payment_method, status)
        VALUES (?, ?, ?, ?, ?, 'Completed')
    ''', (buyer_name, buyer_email, address, total_amount, payment_method))
    order_id = cursor.lastrowid

    for p in paintings:
        cursor.execute('''
            INSERT INTO order_items (order_id, painting_id, price, artist_id)
            VALUES (?, ?, ?, ?)
        ''', (order_id, p['id'], p['price'], p['artist_id']))

        cursor.execute('''
            UPDATE paintings SET status = 'Sold' WHERE id = ?
        ''', (p['id'],))

    conn.commit()
    conn.close()

    session['cart'] = []

    return render_template(
        'order_success.html',
        order_id=order_id,
        buyer_name=buyer_name,
        buyer_email=buyer_email,
        address=address,
        total_amount=total_amount,
        paintings=paintings
    )

# ==========================================
# ARTIST PORTAL & SALES DETAILS
# ==========================================

@app.route('/artist/select/<int:artist_id>')
def select_active_artist(artist_id):
    session['active_artist_id'] = artist_id
    flash('Artist profile switched.', 'info')
    return redirect(url_for('artist_dashboard'))

@app.route('/artist/dashboard')
def artist_dashboard():
    artist_id = session.get('active_artist_id', 1)
    conn = get_db_connection()

    artist = conn.execute('SELECT * FROM artists WHERE id = ?', (artist_id,)).fetchone()
    if not artist:
        first_artist = conn.execute('SELECT * FROM artists ORDER BY id ASC LIMIT 1').fetchone()
        if first_artist:
            artist_id = first_artist['id']
            artist = first_artist
            session['active_artist_id'] = artist_id
        else:
            conn.close()
            return redirect(url_for('add_artist'))

    paintings = conn.execute('''
        SELECT * FROM paintings 
        WHERE artist_id = ? 
        ORDER BY created_at DESC
    ''', (artist_id,)).fetchall()

    sales_stats = conn.execute('''
        SELECT 
            COUNT(oi.id) AS total_sold_count,
            COALESCE(SUM(oi.price), 0.0) AS total_revenue
        FROM order_items oi
        WHERE oi.artist_id = ?
    ''', (artist_id,)).fetchone()

    total_listed = len(paintings)
    available_count = sum(1 for p in paintings if p['status'] == 'Available')
    sold_count = sales_stats['total_sold_count'] or 0
    total_revenue = sales_stats['total_revenue'] or 0.0

    sales_details = conn.execute('''
        SELECT 
            oi.id AS item_id,
            oi.price AS sale_price,
            p.title AS painting_title,
            p.image_url AS painting_image,
            p.medium AS painting_medium,
            o.id AS order_id,
            o.buyer_name,
            o.buyer_email,
            o.shipping_address,
            o.created_at AS sale_date
        FROM order_items oi
        JOIN paintings p ON oi.painting_id = p.id
        JOIN orders o ON oi.order_id = o.id
        WHERE oi.artist_id = ?
        ORDER BY o.created_at DESC
    ''', (artist_id,)).fetchall()

    all_artists = conn.execute('SELECT * FROM artists ORDER BY name ASC').fetchall()
    conn.close()

    return render_template(
        'artist_dashboard.html',
        artist=artist,
        paintings=paintings,
        total_listed=total_listed,
        available_count=available_count,
        sold_count=sold_count,
        total_revenue=total_revenue,
        sales_details=sales_details,
        all_artists=all_artists
    )

@app.route('/artist/add-painting', methods=['GET', 'POST'])
def add_painting():
    artist_id = session.get('active_artist_id', 1)
    conn = get_db_connection()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        selected_artist_id = request.form.get('artist_id', artist_id)
        description = request.form.get('description', '').strip()
        medium = request.form.get('medium', '').strip()
        dimensions = request.form.get('dimensions', '').strip()
        year = request.form.get('year', 2026)
        price = request.form.get('price', 0)
        image_url_input = request.form.get('image_url', '').strip()
        featured = 1 if request.form.get('featured') else 0

        final_image_url = ''

        if 'image_file' in request.files:
            file = request.files['image_file']
            if file and file.filename != '' and allowed_file(file.filename):
                try:
                    filename = secure_filename(f"art_{file.filename}")
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    final_image_url = f"/static/uploads/{filename}"
                except Exception as e:
                    print(f"File save error: {e}")

        if not final_image_url and image_url_input:
            final_image_url = image_url_input
        elif not final_image_url:
            final_image_url = "https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?auto=format&fit=crop&w=1000&q=80"

        try:
            price_val = float(price)
            year_val = int(year)
        except ValueError:
            flash('Invalid price or year format.', 'error')
            return redirect(url_for('add_painting'))

        if not title or not medium or not dimensions:
            flash('Please provide painting title, medium, and dimensions.', 'error')
            return redirect(url_for('add_painting'))

        conn.execute('''
            INSERT INTO paintings (artist_id, title, description, medium, dimensions, year, price, image_url, status, featured)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Available', ?)
        ''', (selected_artist_id, title, description, medium, dimensions, year_val, price_val, final_image_url, featured))
        conn.commit()
        conn.close()

        flash(f'Painting "{title}" uploaded successfully and is now live for sale!', 'success')
        return redirect(url_for('artist_dashboard'))

    artists = conn.execute('SELECT * FROM artists ORDER BY name ASC').fetchall()
    active_artist = conn.execute('SELECT * FROM artists WHERE id = ?', (artist_id,)).fetchone()
    conn.close()

    return render_template('add_painting.html', artists=artists, active_artist=active_artist)

@app.route('/artist/toggle-status/<int:painting_id>', methods=['POST'])
def toggle_painting_status(painting_id):
    conn = get_db_connection()
    painting = conn.execute('SELECT * FROM paintings WHERE id = ?', (painting_id,)).fetchone()
    if painting:
        new_status = 'Sold' if painting['status'] == 'Available' else 'Available'
        conn.execute('UPDATE paintings SET status = ? WHERE id = ?', (new_status, painting_id))
        conn.commit()
        flash(f'Status for "{painting["title"]}" updated to {new_status}.', 'success')
    conn.close()
    return redirect(url_for('artist_dashboard'))

@app.route('/artist/delete-painting/<int:painting_id>', methods=['POST'])
def delete_painting(painting_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM paintings WHERE id = ?', (painting_id,))
    conn.commit()
    conn.close()
    flash('Painting removed from your gallery.', 'info')
    return redirect(url_for('artist_dashboard'))

# ==========================================
# ARTIST DIRECTORY & PROFILES
# ==========================================

@app.route('/artists')
def artists_list():
    conn = get_db_connection()
    artists = conn.execute('''
        SELECT a.*, 
               COUNT(p.id) AS total_paintings,
               SUM(CASE WHEN p.status = 'Available' THEN 1 ELSE 0 END) AS available_paintings
        FROM artists a
        LEFT JOIN paintings p ON a.id = p.artist_id
        GROUP BY a.id
        ORDER BY a.name ASC
    ''').fetchall()
    conn.close()
    return render_template('artists.html', artists=artists)

@app.route('/artist/<int:artist_id>')
def artist_profile(artist_id):
    conn = get_db_connection()
    artist = conn.execute('SELECT * FROM artists WHERE id = ?', (artist_id,)).fetchone()
    if not artist:
        conn.close()
        flash('Artist not found.', 'error')
        return redirect(url_for('artists_list'))

    paintings = conn.execute('''
        SELECT * FROM paintings 
        WHERE artist_id = ? 
        ORDER BY created_at DESC
    ''', (artist_id,)).fetchall()

    conn.close()
    return render_template('artist_profile.html', artist=artist, paintings=paintings)

@app.route('/artist/new', methods=['GET', 'POST'])
def add_artist():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        bio = request.form.get('bio', '').strip()
        location = request.form.get('location', '').strip()
        avatar_url = request.form.get('avatar_url', '').strip()

        if not avatar_url:
            avatar_url = "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=400&q=80"

        if not name or not email:
            flash('Name and email are required.', 'error')
            return redirect(url_for('add_artist'))

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO artists (name, email, bio, location, avatar_url)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, email, bio, location, avatar_url))
            conn.commit()
            new_id = cursor.lastrowid
            session['active_artist_id'] = new_id
            conn.close()
            flash(f'Welcome, {name}! Your artist studio account has been created.', 'success')
            return redirect(url_for('artist_dashboard'))
        except sqlite3.IntegrityError:
            conn.close()
            flash('An artist with this email already exists.', 'error')
            return redirect(url_for('add_artist'))

    return render_template('add_artist.html')

if __name__ == '__main__':
    init_db()
    print("Artisan Canvas starting at http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
