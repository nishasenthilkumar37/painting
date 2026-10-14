# Artisan Canvas — Fine Art Painting Marketplace

An open fine art marketplace built with **Python, HTML5, CSS3, and SQL (SQLite)** designed for independent painters and art collectors.

---

## 🎨 Color Theme & Design System
Crafted strictly according to your palette:
- **Soft White** (`#FAF9F6` & `#F3F5F0`): Clean, breathable gallery background and card surfaces.
- **Sage Green** (`#8A9A86` & `#DFE7DC`): Elegant accent badges, buttons, borders, and highlight pills.
- **Deep Olive** (`#2F3E2E` & `#1E291D`): Refined luxury headers, primary buttons, footers, and price typography.

---

## 🌟 Key Features

### 1. 🖼️ Gallery & Marketplace (`/`)
- Open to all painting artists and collectors.
- **Filters & Search**: Filter by **Medium** (*Oil on Canvas, Watercolor, Acrylic, Gouache, Mixed Media*), **Artist**, **Availability** (*Available vs Sold*), and **Sort by Price or Date**.
- **Painting Cards**: Displays high-resolution painting image, title, artist name & avatar, dimensions, medium, price in deep olive, availability badge, and **+ Cart** quick action.

### 2. 🔍 Painting Detail View (`/painting/<id>`)
- Detailed artwork presentation with dimensions, medium, year, and framing/CoA specs.
- Comprehensive artist biography, location, and studio contact.
- **Add to Collection Cart** or view acquisition status if sold.
- "More from this Artist" showcase.

### 3. 🛒 Cart Navigation & Checkout (`/cart`)
- Persistent live cart counter in top navigation.
- Artwork breakdown with thumbnail, artist, medium, and price.
- Fine art packaging and insurance summary.
- **Direct Checkout Form**: Captures collector name, email, and shipping address, creates an order in the SQL database, links order items to artists, and marks paintings as **Sold**.

### 4. 👩‍🎨 Painter Studio & Sales Details (`/artist/dashboard`)
- **Sales Metrics**:
  - Total Sales Revenue ($)
  - Number of Paintings Sold
  - Available Originals in Studio
  - Total Listed Works
- **Painting Sales Details Table**:
  - Detailed real-time records showing painting title, thumbnail, buyer name, buyer email, shipping destination address, date sold, and sale amount.
- **Inventory & Artwork Management**:
  - Manage all pieces by the artist.
  - One-click toggle between **Available** and **Sold**.
  - Delete or inspect public listing.
  - Multi-artist switcher to test and manage different painter profiles.

### 5. ➕ Upload / Add Painting (`/artist/add-painting`)
- Available for any artist to upload new pieces.
- Form fields: Artwork Title, Artist Selector, Medium, Dimensions, Year, Price ($), Description.
- **Live Image Preview**: Supports both direct device file upload (`/static/uploads/`) and image URLs with live visual preview.

### 6. 👥 Artist Directory & Profiles (`/artists`, `/artist/<id>`, `/artist/new`)
- Directory of all registered painters.
- Profile page showing the artist's full biography and studio catalog.
- Registration form for any new artist wanting to join and sell paintings.

---

## 🗄️ SQL Database Schema (`database.py`)

- **`artists`**: `id`, `name`, `email`, `bio`, `location`, `avatar_url`, `created_at`
- **`paintings`**: `id`, `artist_id`, `title`, `description`, `medium`, `dimensions`, `year`, `price`, `image_url`, `status` (*'Available' | 'Sold'*), `featured`, `created_at`
- **`orders`**: `id`, `buyer_name`, `buyer_email`, `shipping_address`, `total_amount`, `payment_method`, `status`, `created_at`
- **`order_items`**: `id`, `order_id`, `painting_id`, `price`, `artist_id`

---

## 🚀 How to Run

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Application**:
   ```bash
   python app.py
   ```

3. **Open in Browser**:
   Visit [http://127.0.0.1:5000](http://127.0.0.1:5000)

4. **Run Unit Tests**:
   ```bash
   python -m unittest test_app.py
   ```
