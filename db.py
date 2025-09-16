import sqlite3

DB_PATH = "foodbot.db"

# ------------------------------
# Initialize database and tables
# ------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS orders_table (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        created_by INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS menus (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        price INTEGER NOT NULL,
        FOREIGN KEY(order_id) REFERENCES orders_table(id)
    );

    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        fullname TEXT NOT NULL,
        username TEXT
    );

    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        menu_id INTEGER NOT NULL,
        order_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        status TEXT DEFAULT 'pending',
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(menu_id) REFERENCES menus(id),
        FOREIGN KEY(order_id) REFERENCES orders_table(id)
    );

    CREATE TABLE IF NOT EXISTS cart (
        user_id INTEGER,
        order_id INTEGER,
        menu_id INTEGER,
        quantity INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, order_id, menu_id)
    );
    """)
    conn.commit()
    conn.close()


# ------------------------------
# User functions
# ------------------------------
def add_user(user_id, fullname, username):
    """
    Add a new user or update existing user.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (id, fullname, username) 
        VALUES (?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET 
            fullname = excluded.fullname,
            username = excluded.username
    """, (user_id, fullname, username))
    conn.commit()
    conn.close()


def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, fullname, username FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user


def update_user_name(user_id, new_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET fullname = ? WHERE id = ?", (new_name, user_id))
    conn.commit()
    conn.close()


# ------------------------------
# Order functions
# ------------------------------
def create_order(title, created_by):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO orders_table (title, created_by) VALUES (?, ?)", (title, created_by))
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return order_id


def get_order(order_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, created_by FROM orders_table WHERE id = ?", (order_id,))
    order = cursor.fetchone()
    conn.close()
    return order


def add_menu(order_id, name, price):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO menus (order_id, name, price) VALUES (?, ?, ?)", (order_id, name, price))
    conn.commit()
    conn.close()


def get_menus(order_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price FROM menus WHERE order_id = ?", (order_id,))
    menus = cursor.fetchall()
    conn.close()
    return menus


# ------------------------------
# Cart functions
# ------------------------------
def update_cart(user_id, order_id, menu_id, qty_change):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT quantity FROM cart WHERE user_id = ? AND order_id = ? AND menu_id = ?",
                   (user_id, order_id, menu_id))
    row = cursor.fetchone()
    if row:
        new_qty = max(0, row[0] + qty_change)
        cursor.execute("UPDATE cart SET quantity = ? WHERE user_id = ? AND order_id = ? AND menu_id = ?",
                       (new_qty, user_id, order_id, menu_id))
        if new_qty == 0:
            cursor.execute("DELETE FROM cart WHERE user_id = ? AND order_id = ? AND menu_id = ?",
                           (user_id, order_id, menu_id))
    else:
        if qty_change > 0:
            cursor.execute("INSERT INTO cart (user_id, order_id, menu_id, quantity) VALUES (?, ?, ?, ?)",
                           (user_id, order_id, menu_id, qty_change))
    conn.commit()
    conn.close()


def get_cart(user_id, order_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT m.id, m.name, m.price, c.quantity
    FROM cart c
    JOIN menus m ON c.menu_id = m.id
    WHERE c.user_id = ? AND c.order_id = ?
    """, (user_id, order_id))
    cart = cursor.fetchall()
    conn.close()
    return cart


def clear_cart(user_id, order_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cart WHERE user_id = ? AND order_id = ?", (user_id, order_id))
    conn.commit()
    conn.close()


# ------------------------------
# Order finalization
# ------------------------------
def add_order(user_id, order_id, menu_id, quantity):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO order_items (user_id, order_id, menu_id, quantity) VALUES (?, ?, ?, ?)",
                   (user_id, order_id, menu_id, quantity))
    conn.commit()
    conn.close()


# ------------------------------
# Report
# ------------------------------
def get_report(order_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT m.name, SUM(oi.quantity) as total, SUM(oi.quantity * m.price) as total_price
    FROM order_items oi
    JOIN menus m ON oi.menu_id = m.id
    WHERE oi.order_id = ?
    GROUP BY oi.menu_id
    """, (order_id,))
    report = cursor.fetchall()
    conn.close()
    return report
def get_cart_report_summary(order_id):
    """
    Returns a summary report from the cart table:
    - For each user: items and quantities
    - Total quantities per item across all users
    Output format:
    {
        "users": {
            user_fullname: {item_name: quantity, ...},
            ...
        },
        "totals": {
            item_name: total_quantity,
            ...
        }
    }
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # گرفتن تمامی آیتم‌ها و تعداد هر کاربر
    cursor.execute("""
        SELECT u.fullname, m.name, c.quantity
        FROM cart c
        JOIN users u ON c.user_id = u.id
        JOIN menus m ON c.menu_id = m.id
        WHERE c.order_id = ?
    """, (order_id,))
    rows = cursor.fetchall()

    conn.close()

    report = {"users": {}, "totals": {}}

    for fullname, item_name, qty in rows:
        # اضافه کردن به کاربران
        if fullname not in report["users"]:
            report["users"][fullname] = {}
        report["users"][fullname][item_name] = report["users"][fullname].get(item_name, 0) + qty

        # اضافه کردن به مجموع کل
        report["totals"][item_name] = report["totals"].get(item_name, 0) + qty

    return report
def get_cart_report_with_prices(order_id):
    """
    Returns a summary report from the cart table including prices:
    - For each user: items, quantities, total price per item
    - Total quantities and total prices per item across all users
    - Grand total
    Output format:
    {
        "users": {
            user_fullname: {item_name: {"quantity": x, "total_price": y}, ...},
            ...
        },
        "totals": {
            item_name: {"quantity": total_qty, "total_price": total_price},
            ...
        },
        "grand_total": total_amount
    }
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # گرفتن همه آیتم‌ها و تعداد هر کاربر و قیمت منو
    cursor.execute("""
        SELECT u.fullname, m.name, c.quantity, m.price
        FROM cart c
        JOIN users u ON c.user_id = u.id
        JOIN menus m ON c.menu_id = m.id
        WHERE c.order_id = ?
    """, (order_id,))
    rows = cursor.fetchall()
    conn.close()

    report = {"users": {}, "totals": {}, "grand_total": 0}

    for fullname, item_name, qty, price in rows:
        item_total = qty * price

        # کاربران
        if fullname not in report["users"]:
            report["users"][fullname] = {}
        report["users"][fullname][item_name] = {
            "quantity": qty,
            "total_price": item_total
        }

        # مجموع کل آیتم
        if item_name not in report["totals"]:
            report["totals"][item_name] = {"quantity": 0, "total_price": 0}
        report["totals"][item_name]["quantity"] += qty
        report["totals"][item_name]["total_price"] += item_total

        # جمع کل نهایی
        report["grand_total"] += item_total

    return report
