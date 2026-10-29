import sqlite3

DB_NAME = "labubu_shop.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Products table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            image_url TEXT
        )
    ''')
    
    # Promocodes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS promocodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            discount_percent REAL DEFAULT 10.0
        )
    ''')
    
    # Settings table (Card details)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # Orders table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_name TEXT,
            phone TEXT,
            region TEXT,
            product_name TEXT,
            original_price REAL,
            final_price REAL,
            promo_used TEXT,
            status TEXT DEFAULT 'Yangi',
            check_file_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('card_number', '8600 0000 0000 0000')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('card_holder', 'ABE VAYN')")
    cursor.execute("INSERT OR IGNORE INTO promocodes (code, discount_percent) VALUES ('ABE10', 10.0)")
    
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO products (name, price, image_url) VALUES ('Labubu Classic Toy', 20000, '/static/labubu.png')")

    conn.commit()
    conn.close()

def get_setting(key):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else ""

def set_setting(key, value):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def validate_promo(code):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT discount_percent FROM promocodes WHERE code=?", (code.upper(),))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else None

def add_promocode(code, percent=10.0):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO promocodes (code, discount_percent) VALUES (?, ?)", (code.upper(), percent))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False

def add_order(user_id, user_name, phone, region, product_name, orig_price, final_price, promo, check_file_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO orders (user_id, user_name, phone, region, product_name, original_price, final_price, promo_used, check_file_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, user_name, phone, region, product_name, orig_price, final_price, promo, check_file_id))
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return order_id

def update_order_status(order_id, status):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
    conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), SUM(final_price) FROM orders")
    res = cursor.fetchone()
    conn.close()
    return res[0] or 0, res[1] or 0.0
