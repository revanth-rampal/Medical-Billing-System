-- schema.sql
DROP TABLE IF EXISTS medicines;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS bills;
DROP TABLE IF EXISTS bill_items;
DROP TABLE IF EXISTS app_settings; -- New table for application settings

CREATE TABLE medicines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    barcode TEXT,
    medicineName TEXT NOT NULL,
    batchNo TEXT NOT NULL,
    mrp REAL,
    sellingPrice REAL, -- This will be the default price per unit for billing
    mfgDate TEXT NOT NULL,
    expiryDate TEXT NOT NULL,
    quantity INTEGER NOT NULL, -- Stock quantity
    supplier TEXT,
    shelfNo TEXT,
    boxNo TEXT,
    shop_id TEXT, -- Optional ID for the medicine itself (e.g., internal code)
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone_number TEXT NOT NULL UNIQUE,
    email TEXT,
    address TEXT,
    registered_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE bills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER, -- Can be NULL if customer is not registered (e.g., walk-in)
    customer_phone_temp TEXT, -- To store phone if customer_id is NULL
    customer_name_temp TEXT, -- To store name if customer_id is NULL
    total_amount REAL NOT NULL,
    bill_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    billed_from_shop_id TEXT, -- Optional: An identifier for the shop/terminal generating the bill
    FOREIGN KEY (customer_id) REFERENCES customers (id)
);

CREATE TABLE bill_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id INTEGER NOT NULL,
    medicine_id INTEGER NOT NULL,
    medicine_name_snapshot TEXT NOT NULL, -- Name of medicine at the time of billing
    quantity_billed INTEGER NOT NULL,
    price_per_unit_at_billing REAL NOT NULL, -- Price at which it was sold
    total_price_for_item REAL NOT NULL,
    FOREIGN KEY (bill_id) REFERENCES bills (id),
    FOREIGN KEY (medicine_id) REFERENCES medicines (id)
);

-- New table for application-wide settings like UPI details
CREATE TABLE app_settings (
    setting_key TEXT PRIMARY KEY NOT NULL,
    setting_value TEXT
);

-- Pre-populate with default empty UPI settings to avoid errors on first run
-- The admin will update these via the admin panel.
INSERT OR IGNORE INTO app_settings (setting_key, setting_value) VALUES ('upi_id', '');
INSERT OR IGNORE INTO app_settings (setting_key, setting_value) VALUES ('payee_name', '');

