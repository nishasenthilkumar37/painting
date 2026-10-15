import sqlite3
import os
import shutil

IS_SERVERLESS = bool(os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if IS_SERVERLESS:
    DB_PATH = '/tmp/artisan_gallery.db'
    bundled_db = os.path.join(BASE_DIR, 'artisan_gallery.db')
    if not os.path.exists(DB_PATH) and os.path.exists(bundled_db):
        try:
            shutil.copyfile(bundled_db, DB_PATH)
        except Exception:
            pass
else:
    DB_PATH = os.path.join(BASE_DIR, 'artisan_gallery.db')

_FIXED_URLS = False

def fix_known_broken_urls(conn):
    global _FIXED_URLS
    if _FIXED_URLS:
        return
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='paintings'")
        if not cur.fetchone():
            return
        # Fix Sage Horizons No. 4
        cur.execute("""
            UPDATE paintings 
            SET image_url = 'https://images.unsplash.com/photo-1580136579312-94651dfd596d?auto=format&fit=crop&w=1200&q=80'
            WHERE title = 'Sage Horizons No. 4' OR image_url LIKE '%photo-1579783902614%'
        """)
        # Fix Zen Garden Stone and Moss
        cur.execute("""
            UPDATE paintings 
            SET image_url = 'https://images.unsplash.com/photo-1578301978693-85fa9c0320b9?auto=format&fit=crop&w=1200&q=80'
            WHERE title = 'Zen Garden Stone and Moss' OR image_url LIKE '%photo-1549887534%'
        """)
        conn.commit()
        _FIXED_URLS = True
    except Exception:
        pass

def get_db_connection():
    if not os.path.exists(DB_PATH):
        init_db()

    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM artists LIMIT 1")
    except sqlite3.OperationalError:
        conn.close()
        init_db()
        conn = sqlite3.connect(DB_PATH, timeout=20.0)
        conn.row_factory = sqlite3.Row

    fix_known_broken_urls(conn)
    return conn

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Artists table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS artists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            bio TEXT,
            location TEXT,
            avatar_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Paintings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS paintings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            artist_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            medium TEXT NOT NULL,
            dimensions TEXT NOT NULL,
            year INTEGER,
            price REAL NOT NULL,
            image_url TEXT NOT NULL,
            status TEXT DEFAULT 'Available',
            featured INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (artist_id) REFERENCES artists (id) ON DELETE CASCADE
        )
    ''')

    # Orders table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            buyer_name TEXT NOT NULL,
            buyer_email TEXT NOT NULL,
            shipping_address TEXT NOT NULL,
            total_amount REAL NOT NULL,
            payment_method TEXT DEFAULT 'Credit Card (Simulated)',
            status TEXT DEFAULT 'Completed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Order items table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            painting_id INTEGER NOT NULL,
            price REAL NOT NULL,
            artist_id INTEGER NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE CASCADE,
            FOREIGN KEY (painting_id) REFERENCES paintings (id),
            FOREIGN KEY (artist_id) REFERENCES artists (id)
        )
    ''')

    conn.commit()

    # Seed data if artists table is empty
    cursor.execute('SELECT COUNT(*) FROM artists')
    if cursor.fetchone()[0] == 0:
        seed_sample_data(conn)

    conn.close()

def seed_sample_data(conn):
    cursor = conn.cursor()

    sample_artists = [
        (
            "Elena Rostova",
            "elena.art@gallery.com",
            "Contemporary impressionist painter inspired by Nordic landscapes, misty horizons, and botanical quietude. Works primarily in layered oil and palette knife textures.",
            "Stockholm, Sweden",
            "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=400&q=80"
        ),
        (
            "Marcus Thorne",
            "marcus.thorne@canvas.org",
            "Abstract expressionist focusing on earthy pigments, raw linen surfaces, and deep meditative olive and sage tones. Exhibited across Europe and North America.",
            "Florence, Italy",
            "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=400&q=80"
        ),
        (
            "Aria Chen",
            "aria.chen.studio@atelier.com",
            "Botanical watercolorist and oil painter. Specializes in quiet morning flora, translucent washes, and delicate natural geometry.",
            "Vancouver, Canada",
            "https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=400&q=80"
        ),
        (
            "Julian Vance",
            "julian.vance@fineart.net",
            "Modern minimalist exploring geometric harmony, textured acrylic pastes, and tranquil organic palettes for architectural spaces.",
            "Kyoto, Japan",
            "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=400&q=80"
        )
    ]

    cursor.executemany('''
        INSERT INTO artists (name, email, bio, location, avatar_url)
        VALUES (?, ?, ?, ?, ?)
    ''', sample_artists)

    sample_paintings = [
        (
            1,
            "Whispering Pines in Morning Mist",
            "A serene oil painting capturing first morning sunlight breaking through quiet evergreen hills. Thick palette knife impasto meets gentle gradient washes.",
            "Oil on Linen",
            '24" x 36"',
            2025,
            1250.00,
            "https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?auto=format&fit=crop&w=1000&q=80",
            "Available",
            1
        ),
        (
            1,
            "Olive Grove at Dusk",
            "Warm twilight settling over ancient silver-green olive branches. Rich textures with subtle golden accents and olive green undertones.",
            "Oil on Canvas",
            '30" x 40"',
            2026,
            1680.00,
            "https://images.unsplash.com/photo-1578925518470-4def7a0f08bb?auto=format&fit=crop&w=1000&q=80",
            "Available",
            1
        ),
        (
            2,
            "Sage Horizons No. 4",
            "An abstract study in sage green and chalky whites. Layered mineral pigments and raw marble dust create a tactile, sculptural surface.",
            "Mixed Media & Acrylic",
            '36" x 36"',
            2025,
            1450.00,
            "https://images.unsplash.com/photo-1580136579312-94651dfd596d?auto=format&fit=crop&w=1200&q=80",
            "Available",
            1
        ),
        (
            2,
            "Deep Earth Harmony",
            "Deep olive, umber, and soft ecru converge in rhythmic horizontal passages. Evokes ancient geological layers and quiet contemplation.",
            "Oil and Sand on Canvas",
            '20" x 30"',
            2024,
            980.00,
            "https://images.unsplash.com/photo-1541701494587-cb58502866ab?auto=format&fit=crop&w=1000&q=80",
            "Sold",
            0
        ),
        (
            3,
            "Botanical Solitude: Wild Eucalyptus",
            "Delicate translucent watercolor wash depicting swaying wild eucalyptus branches. Rendered on 300gsm cold-pressed cotton paper.",
            "Watercolor on Cotton Paper",
            '18" x 24"',
            2026,
            720.00,
            "https://images.unsplash.com/photo-1579783928621-7a13d66a62d1?auto=format&fit=crop&w=1000&q=80",
            "Available",
            0
        ),
        (
            3,
            "Ferns of the Valleys",
            "Intricate botanical study of woodland ferns with layered emerald, sage, and deep forest moss pigments on custom framed archival linen.",
            "Gouache and Ink",
            '16" x 20"',
            2025,
            640.00,
            "https://images.unsplash.com/photo-1582561424760-0321d75e81fa?auto=format&fit=crop&w=1000&q=80",
            "Available",
            0
        ),
        (
            4,
            "Zen Garden Stone and Moss",
            "Minimalist composition exploring organic forms, silent negative spaces, and refined olive textures. Perfect for contemporary architectural spaces.",
            "Textured Acrylic on Canvas",
            '48" x 36"',
            2026,
            2100.00,
            "https://images.unsplash.com/photo-1578301978693-85fa9c0320b9?auto=format&fit=crop&w=1200&q=80",
            "Available",
            1
        ),
        (
            4,
            "Reflections in Still Water",
            "Subdued sage and soft ivory gradients mirroring still pond currents under morning fog. A calming meditative centerpiece.",
            "Acrylic and Oil Glaze",
            '30" x 30"',
            2025,
            1150.00,
            "https://images.unsplash.com/photo-1577083552431-6e5fd01aa342?auto=format&fit=crop&w=1000&q=80",
            "Sold",
            0
        )
    ]

    cursor.executemany('''
        INSERT INTO paintings (
            artist_id, title, description, medium, dimensions, year, price, image_url, status, featured
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', sample_paintings)

    cursor.execute('''
        INSERT INTO orders (buyer_name, buyer_email, shipping_address, total_amount, payment_method, status, created_at)
        VALUES ('Lady Genevieve Clark', 'g.clark@heritage.co.uk', '44 Kensington Gardens, London, UK', 2130.00, 'MasterCard •••• 4892', 'Completed', '2026-09-28 14:22:00')
    ''')
    order_id = cursor.lastrowid

    cursor.execute('''
        INSERT INTO order_items (order_id, painting_id, price, artist_id)
        VALUES (?, 4, 980.00, 2)
    ''', (order_id,))

    cursor.execute('''
        INSERT INTO order_items (order_id, painting_id, price, artist_id)
        VALUES (?, 8, 1150.00, 4)
    ''', (order_id,))

    conn.commit()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully.")
