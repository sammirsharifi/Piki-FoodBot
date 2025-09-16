-- Orders table (formerly campaigns)
CREATE TABLE IF NOT EXISTS orders_table (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Menus belong to an order
CREATE TABLE IF NOT EXISTS menus (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    price INTEGER NOT NULL,
    FOREIGN KEY(order_id) REFERENCES orders_table(id)
);

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    fullname TEXT,
    username TEXT
);

-- Order items linked to order and menu
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

-- Cart linked to order
CREATE TABLE IF NOT EXISTS cart (
    user_id INTEGER,
    order_id INTEGER,
    menu_id INTEGER,
    quantity INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, order_id, menu_id)
);