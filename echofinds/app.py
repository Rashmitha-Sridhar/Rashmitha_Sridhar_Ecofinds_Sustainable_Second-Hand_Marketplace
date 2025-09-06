from flask import Flask, render_template, request, redirect, session, url_for
import db
import os
import time
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "supersecretkey"  # required for session management

# Directory to store uploaded product images (relative to project)
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Root route to avoid "URL not found" when visiting /
@app.route("/")
def index():
    # send logged-in users to dashboard, others to login
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


# Keep the session cart in sync with products table: remove ids that were deleted
@app.before_request
def sanitize_cart():
    cart = session.get('cart', [])
    if not cart:
        return
    # check which ids still exist in products
    try:
        conn = db.get_db_connection()
        cursor = conn.cursor(dictionary=True)
        unique_ids = sorted(set(cart))
        placeholders = ','.join(['%s'] * len(unique_ids))
        query = f"SELECT id FROM products WHERE id IN ({placeholders})"
        cursor.execute(query, tuple(unique_ids))
        rows = cursor.fetchall()
        existing = {r['id'] for r in rows}
        cursor.close()
        conn.close()
        if existing:
            new_cart = [pid for pid in cart if pid in existing]
        else:
            new_cart = []
        if len(new_cart) != len(cart):
            session['cart'] = new_cart
    except Exception:
        # If DB check fails, silently continue (don't break requests)
        pass


# Simple 404 handler to redirect unknown URLs to index
@app.errorhandler(404)
def page_not_found(e):
    return redirect(url_for("index"))


# ------------------ AUTH ------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        conn = db.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                       (username, email, password))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect("/login")
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = db.get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email=%s AND password=%s", (email, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect("/dashboard")
        else:
            return "Invalid Credentials"
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ------------------ DASHBOARD ------------------
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id=%s", (session["user_id"],))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    # also fetch all products to show on the landing dashboard
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products ORDER BY id DESC")
    products = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("dashboard.html", user=user, products=products)


# ------------------ PRODUCTS ------------------
@app.route("/products")
def products():
    # support simple search via ?q= term
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    # build base query and params
    if q and category:
        like = f"%{q}%"
        cursor.execute("SELECT * FROM products WHERE (title LIKE %s OR description LIKE %s) AND category=%s", (like, like, category))
    elif q:
        like = f"%{q}%"
        cursor.execute("SELECT * FROM products WHERE title LIKE %s OR description LIKE %s", (like, like))
    elif category:
        cursor.execute("SELECT * FROM products WHERE category=%s", (category,))
    else:
        cursor.execute("SELECT * FROM products")
    items = cursor.fetchall()
    # fetch categories for filter dropdown
    cursor.execute("SELECT DISTINCT category FROM products WHERE category IS NOT NULL AND category <> ''")
    cats = cursor.fetchall()
    categories = [c['category'] for c in cats]
    cursor.close()
    conn.close()
    return render_template("products.html", products=items, q=q, categories=categories, category=category)


@app.route('/products/<int:product_id>')
def product_detail(product_id):
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT p.*, u.username as seller FROM products p LEFT JOIN users u ON p.user_id=u.id WHERE p.id=%s', (product_id,))
    prod = cursor.fetchone()
    cursor.close()
    conn.close()
    if not prod:
        return redirect(url_for('products'))
    return render_template('product_detail.html', product=prod)


@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM products WHERE id=%s', (product_id,))
    prod = cursor.fetchone()
    if not prod:
        cursor.close()
        conn.close()
        return redirect(url_for('dashboard'))

    # only owner can edit
    if prod.get('user_id') != session.get('user_id'):
        cursor.close()
        conn.close()
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category = request.form.get('category')
        price = request.form.get('price')

        # optional new image
        image_filename = prod.get('image_url')
        if 'image' in request.files:
            f = request.files['image']
            if f and f.filename:
                filename = secure_filename(f.filename)
                filename = f"{session['user_id']}_{int(time.time())}_{filename}"
                dest = os.path.join(UPLOAD_DIR, filename)
                f.save(dest)
                print(f"Saved uploaded image (edit): {dest}")
                image_filename = filename

        upd_cursor = conn.cursor()
        upd_cursor.execute('UPDATE products SET title=%s, description=%s, category=%s, price=%s, image_url=%s WHERE id=%s',
                           (title, description, category, price, image_filename, product_id))
        conn.commit()
        upd_cursor.close()
        cursor.close()
        conn.close()
        return redirect(url_for('dashboard'))

    cursor.close()
    conn.close()
    return render_template('edit_product.html', product=prod)


@app.route('/checkout', methods=['POST'])
def checkout():
    # move items from cart to session orders as a simple purchase record
    cart = session.get('cart', [])
    if not cart:
        return redirect(url_for('cart'))
    # If user is logged in, persist to DB (orders + order_items). Otherwise use session orders.
    if session.get('user_id'):
        conn = db.get_db_connection()
        cursor = conn.cursor()
        # ensure tables exist (simple schema creation; idempotent)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INT PRIMARY KEY AUTO_INCREMENT,
                user_id INT,
                created_at BIGINT
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                id INT PRIMARY KEY AUTO_INCREMENT,
                order_id INT,
                product_id INT
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        ''')
        conn.commit()

        cursor.execute('INSERT INTO orders (user_id, created_at) VALUES (%s,%s)', (session['user_id'], int(time.time())))
        order_id = cursor.lastrowid
        if cart:
            for pid in cart:
                cursor.execute('INSERT INTO order_items (order_id, product_id) VALUES (%s,%s)', (order_id, pid))
        conn.commit()
        cursor.close()
        conn.close()
        session['cart'] = []
        return redirect(url_for('order_success', order_id=order_id))
    else:
        orders = session.get('orders', [])
        timestamp = int(time.time())
        orders.append({'items': cart.copy(), 'timestamp': timestamp})
        session['orders'] = orders
        session['cart'] = []
        # for guests create a temporary order id (timestamp)
        return redirect(url_for('order_success', order_id=timestamp))


@app.route('/order_success')
def order_success():
    order_id = request.args.get('order_id')
    if not order_id:
        return redirect(url_for('products'))

    # if logged-in and order_id is numeric, fetch persisted order
    if session.get('user_id'):
        try:
            oid = int(order_id)
        except Exception:
            return redirect(url_for('products'))
        conn = db.get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM orders WHERE id=%s AND user_id=%s', (oid, session['user_id']))
        order = cursor.fetchone()
        if not order:
            cursor.close()
            conn.close()
            return redirect(url_for('products'))
        cursor.execute('SELECT p.* FROM order_items oi JOIN products p ON oi.product_id=p.id WHERE oi.order_id=%s', (oid,))
        items = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('order_success.html', order={'id': oid, 'timestamp': order.get('created_at')}, items=items)

    # guest: order_id is the timestamp; find matching session order
    orders = session.get('orders', [])
    for o in orders:
        if str(o.get('timestamp')) == str(order_id):
            ids = o.get('items', [])
            if not ids:
                return render_template('order_success.html', order={'id': order_id, 'timestamp': o.get('timestamp')}, items=[])
            conn = db.get_db_connection()
            cursor = conn.cursor(dictionary=True)
            placeholders = ','.join(['%s'] * len(ids))
            query = f"SELECT * FROM products WHERE id IN ({placeholders})"
            cursor.execute(query, tuple(ids))
            items = cursor.fetchall()
            cursor.close()
            conn.close()
            return render_template('order_success.html', order={'id': order_id, 'timestamp': o.get('timestamp')}, items=items)

    return redirect(url_for('products'))


@app.route('/previous_purchases')
def previous_purchases():
    # Show previous purchases for logged-in users or session-stored orders for guests
    detailed_orders = []

    if session.get('user_id'):
        conn = db.get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM orders WHERE user_id=%s ORDER BY created_at DESC', (session['user_id'],))
        db_orders = cursor.fetchall() or []
        for o in db_orders:
            cursor.execute('SELECT p.* FROM order_items oi JOIN products p ON oi.product_id=p.id WHERE oi.order_id=%s', (o['id'],))
            prods = cursor.fetchall() or []
            # filter out any None rows (product may have been deleted)
            prods = [p for p in prods if p]
            detailed_orders.append({'timestamp': o.get('created_at'), 'products': prods})
        cursor.close()
        conn.close()
        return render_template('previous_purchases.html', orders=detailed_orders, q='', categories=[])

    # Guest orders stored in session
    orders = session.get('orders', [])
    if not orders:
        return render_template('previous_purchases.html', orders=[], q='', categories=[])

    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    for o in orders:
        ids = o.get('items', [])
        if not ids:
            detailed_orders.append({'timestamp': o.get('timestamp'), 'products': []})
            continue
        placeholders = ','.join(['%s'] * len(ids))
        query = f"SELECT * FROM products WHERE id IN ({placeholders})"
        cursor.execute(query, tuple(ids))
        prods = cursor.fetchall() or []
        prods = [p for p in prods if p]
        detailed_orders.append({'timestamp': o.get('timestamp'), 'products': prods})
    cursor.close()
    conn.close()
    return render_template('previous_purchases.html', orders=detailed_orders, q='', categories=[])


@app.route('/debug_last_product')
def debug_last_product():
    # small debug helper (only in dev) to inspect most recent product row
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM products ORDER BY id DESC LIMIT 1')
    prod = cursor.fetchone()
    cursor.close()
    conn.close()
    return prod or {}


@app.route('/list_uploads')
def list_uploads():
    # show files currently present in the uploads folder (dev helper)
    try:
        files = os.listdir(UPLOAD_DIR)
    except Exception as e:
        return {"error": str(e)}
    return {"files": files}


@app.route('/my_listings')
def my_listings():
    # show products created by the logged-in user
    if "user_id" not in session:
        return redirect(url_for('login'))

    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE user_id=%s", (session['user_id'],))
    items = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('products.html', products=items, mine=True)


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM users WHERE id=%s', (session['user_id'],))
    user = cursor.fetchone()

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        old_profile_image = user.get('profile_image') if user else None
        profile_image = old_profile_image
        if 'image' in request.files:
            f = request.files['image']
            if f and f.filename:
                filename = secure_filename(f.filename)
                filename = f"user_{session['user_id']}_{int(time.time())}_{filename}"
                dest = os.path.join(UPLOAD_DIR, filename)
                f.save(dest)
                print(f"Saved profile image: {dest}")
                profile_image = filename

        upd = conn.cursor()
        # create profile_image column if missing (best-effort)
        try:
            try:
                upd.execute("ALTER TABLE users ADD COLUMN profile_image VARCHAR(255)")
            except Exception:
                # ignore if column already exists or if alter not permitted
                pass

            upd.execute('UPDATE users SET username=%s, email=%s, password=%s, profile_image=%s WHERE id=%s',
                        (username, email, password, profile_image, session['user_id']))
            conn.commit()

            # remove old profile image file if a new one was uploaded
            if old_profile_image and profile_image and old_profile_image != profile_image:
                try:
                    old_path = os.path.join(UPLOAD_DIR, old_profile_image)
                    if os.path.isfile(old_path):
                        os.remove(old_path)
                except Exception as e:
                    print(f"Warning removing old profile image: {e}")

            upd.close()
            cursor.close()
            conn.close()

            # update session username
            session['username'] = username
            # redirect back to profile so the updated image/values are visible
            return redirect(url_for('profile'))
        except Exception as e:
            # rollback and surface the SQL error in the template for debugging
            try:
                conn.rollback()
            except Exception:
                pass
            upd.close()
            cursor.close()
            conn.close()
            # show the error on the profile page so user can see the DB error message
            return render_template('profile.html', user=user, error=str(e))

    cursor.close()
    conn.close()
    return render_template('profile.html', user=user)


@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    # use session to store a simple cart as a list of product ids
    cart = session.get('cart', [])
    cart.append(product_id)
    session['cart'] = cart
    print(f"Cart updated (add): user={session.get('user_id')} size={len(cart)}")
    return redirect(request.referrer or url_for('products'))


@app.route('/add_to_cart', methods=['POST'])
def add_to_cart_form():
    # support forms that post product_id instead of using a URL parameter
    pid = request.form.get('product_id')
    if not pid:
        return redirect(request.referrer or url_for('products'))
    try:
        product_id = int(pid)
    except ValueError:
        return redirect(request.referrer or url_for('products'))

    cart = session.get('cart', [])
    cart.append(product_id)
    session['cart'] = cart
    print(f"Cart updated (add_form): user={session.get('user_id')} size={len(cart)}")
    return redirect(request.referrer or url_for('products'))


@app.route('/remove_from_cart/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    cart = session.get('cart', [])
    # remove first occurrence
    try:
        cart.remove(product_id)
    except ValueError:
        pass
    session['cart'] = cart
    print(f"Cart updated (remove): user={session.get('user_id')} size={len(cart)}")
    return redirect(url_for('cart'))


@app.route('/cart')
def cart():
    cart = session.get('cart', [])
    products_in_cart = []
    total_items = 0
    if cart:
        # fetch product details for unique ids in cart and attach quantities
        from collections import Counter
        counts = Counter(cart)
        ids = list(counts.keys())
        conn = db.get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # build a parameter list for IN clause using unique ids
        placeholders = ','.join(['%s'] * len(ids))
        query = f"SELECT * FROM products WHERE id IN ({placeholders})"
        cursor.execute(query, tuple(ids))
        rows = cursor.fetchall()
        # attach qty for each product row
        for r in rows:
            r['qty'] = counts.get(r['id'], 0)
            total_items += r['qty']
        products_in_cart = rows
        cursor.close()
        conn.close()
        # Remove ids from session cart that no longer exist (keep only product ids present in DB)
        existing_ids = {r['id'] for r in products_in_cart}
        new_cart = [pid for pid in cart if pid in existing_ids]
        if len(new_cart) != len(cart):
            session['cart'] = new_cart

    return render_template('cart.html', products=products_in_cart, total_items=total_items)


@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    # only allow deletion if logged-in user is the owner of the product
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM products WHERE id=%s', (product_id,))
    prod = cursor.fetchone()
    if not prod:
        cursor.close()
        conn.close()
        return redirect(url_for('dashboard'))

    if prod.get('user_id') != session.get('user_id'):
        # not the owner; do not delete
        cursor.close()
        conn.close()
        return redirect(url_for('dashboard'))

    # proceed to delete; first remove uploaded image file if present
    image_filename = prod.get('image_url')
    try:
        if image_filename:
            image_path = os.path.join(UPLOAD_DIR, image_filename)
            if os.path.isfile(image_path):
                os.remove(image_path)
    except Exception as e:
        # log but continue with DB deletion
        print(f"Warning: could not remove image file {image_filename}: {e}")

    cursor.close()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM products WHERE id=%s', (product_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('dashboard'))


@app.route("/add_product", methods=["GET", "POST"])
def add_product():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        category = request.form["category"]
        price = request.form["price"]
        # handle optional image upload
        image_filename = None
        if 'image' in request.files:
            f = request.files['image']
            if f and f.filename:
                filename = secure_filename(f.filename)
                # prefix with user id and timestamp to avoid collisions
                filename = f"{session['user_id']}_{int(time.time())}_{filename}"
                dest = os.path.join(UPLOAD_DIR, filename)
                f.save(dest)
                print(f"Saved uploaded image: {dest}")
                image_filename = filename

        conn = db.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO products (user_id, title, description, category, price, image_url) VALUES (%s,%s,%s,%s,%s,%s)",
            (session["user_id"], title, description, category, price, image_filename))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect("/products")
    return render_template("add_product.html")


if __name__ == "__main__":
    # Run the Flask development server when executed directly
    # Keep debug True for useful debug output, but disable the reloader which
    # can trigger repeated restarts on some Windows filesystems (OneDrive).
    app.run(debug=True, use_reloader=False)
