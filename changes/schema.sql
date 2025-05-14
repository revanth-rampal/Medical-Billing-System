-- schema.sql
DROP TABLE IF EXISTS medicines; -- Remove table if it already exists, for easy re-initialization

CREATE TABLE medicines (
    id INTEGER PRIMARY KEY AUTOINCREMENT, -- Unique ID for each medicine, automatically increments
    barcode TEXT,                         -- Barcode (UPC)
    medicineName TEXT NOT NULL,           -- Name of the medicine (required)
    batchNo TEXT NOT NULL,                -- Batch number (required)
    mrp REAL,                             -- Maximum Retail Price (optional, allows decimals)
    sellingPrice REAL,                    -- Selling Price (optional, allows decimals)
    mfgDate TEXT NOT NULL,                -- Manufacturing date (YYYY-MM-DD format, required)
    expiryDate TEXT NOT NULL,             -- Expiry date (YYYY-MM-DD format, required)
    quantity INTEGER NOT NULL,            -- Quantity (required)
    supplier TEXT,                        -- Supplier name (optional)
    shelfNo TEXT,                         -- Shelf number (optional)
    boxNo TEXT,                           -- Box number (optional)
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP -- Automatically records when the entry was added/modified
);

