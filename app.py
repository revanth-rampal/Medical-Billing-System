# app.py
import sqlite3
import datetime
import logging
import click 
import os 
from flask import Flask, render_template, request, jsonify, g, redirect, url_for, flash

import requests

# --- (API Config, App Init, DB Helpers, Expiry Status, Context Processor - same as before) ---
# Make sure these are present from your existing app_py_update_shopid
try:
    import api
    UPCITEMDB_TRIAL_BASE_URL = api.UPCITEMDB_TRIAL_BASE_URL
except (ImportError, AttributeError) as e:
    UPCITEMDB_TRIAL_BASE_URL = "https://api.upcitemdb.com/prod/trial/lookup"
    logging.warning(f"Could not import UPCITEMDB_TRIAL_BASE_URL from api.py, using default. Error: {e}")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24) 
DATABASE = 'inventory.db'

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s [%(pathname)s:%(lineno)d]')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def table_exists(table_name):
    db = get_db()
    cur = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cur.fetchone() is not None

def init_db():
    with app.app_context():
        db = get_db()
        try:
            with app.open_resource('schema.sql', mode='r') as f:
                db.cursor().executescript(f.read())
            db.commit()
            app.logger.info("Database initialized successfully using schema.sql.")
            if not table_exists('medicines'): app.logger.error("CRITICAL: 'medicines' table NOT created.")
            if not table_exists('customers'): app.logger.error("CRITICAL: 'customers' table NOT created.")
            if not table_exists('bills'): app.logger.error("CRITICAL: 'bills' table NOT created.")
            if not table_exists('bill_items'): app.logger.error("CRITICAL: 'bill_items' table NOT created.")
        except FileNotFoundError: app.logger.error("CRITICAL: schema.sql not found.")
        except Exception as e: app.logger.error(f"CRITICAL: Error initializing database: {e}", exc_info=True)

@app.cli.command('init-db')
def init_db_command():
    if os.path.exists(DATABASE):
        click.echo(f"WARNING: DB '{DATABASE}' exists. Re-initializing will clear all data.")
        if not click.confirm("Continue and re-initialize?"):
            click.echo("Cancelled.")
            return
        try: os.remove(DATABASE); click.echo(f"Removed existing DB '{DATABASE}'.")
        except OSError as e: click.echo(f"Error removing DB: {e}. Remove manually."); return
    init_db()
    click.echo('Initialized the database.')

def get_expiry_status(expiry_date_str):
    # ... (same as before)
    if not expiry_date_str: return {"statusText": "N/A", "statusClass": "badge-secondary", "statusKey": "unknown"}
    today = datetime.date.today()
    try: expiry_date = datetime.datetime.strptime(str(expiry_date_str), '%Y-%m-%d').date()
    except ValueError: return {"statusText": "Invalid Date", "statusClass": "badge-danger", "statusKey": "invalid"}
    if expiry_date < today: return {"statusText": "Expired", "statusClass": "badge-danger", "statusKey": "expired"}
    elif expiry_date <= (today + datetime.timedelta(days=30)): return {"statusText": "Expires Soon", "statusClass": "badge-warning", "statusKey": "soon"}
    else: return {"statusText": "Good", "statusClass": "badge-success", "statusKey": "good"}

@app.context_processor
def inject_now(): return {'SCRIPT_START_TIME': datetime.datetime.utcnow()}

# --- Main Routes (Home, Inventory, Add/Delete Medicine, Barcode Fetch - same as app_py_update_shopid) ---
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/inventory')
def inventory():
    # ... (same as app_py_update_shopid, ensuring shop_id is fetched and passed) ...
    db = get_db()
    if not table_exists('medicines'):
        flash("'medicines' table missing. Run 'flask init-db'.", "error")
        return render_template('inventory.html', medicines=[]), 500
    cur = db.execute("SELECT id, barcode, medicineName, batchNo, mrp, sellingPrice, mfgDate, expiryDate, quantity, supplier, shelfNo, boxNo, shop_id FROM medicines ORDER BY expiryDate ASC")
    medicines_from_db = cur.fetchall()
    medicines_with_status = []
    for row in medicines_from_db:
        med = dict(row); status_info = get_expiry_status(med.get('expiryDate'))
        full_med_info = {**med, **status_info}
        medicines_with_status.append(full_med_info)
    return render_template('inventory.html', medicines=medicines_with_status)

@app.route('/add_medicine', methods=['POST'])
def add_medicine_route():
    # ... (same as app_py_update_shopid, ensuring shop_id is handled) ...
    if not table_exists('medicines'): return jsonify({"success": False, "message": "'medicines' table missing."}), 500
    data = request.get_json()
    if not data: return jsonify({"success": False, "message": "Invalid JSON."}), 400
    # Basic validation
    required = ['medicineName', 'batchNo', 'mfgDate', 'expiryDate', 'quantity']
    if any(not data.get(f) or (isinstance(data.get(f), str) and not data.get(f).strip()) for f in required):
        return jsonify({"success": False, "message": "Missing required fields."}), 400
    # Further specific validations (dates, quantity, prices) should be here as before
    try:
        mfg_date = datetime.datetime.strptime(data['mfgDate'].strip(), '%Y-%m-%d').date()
        exp_date = datetime.datetime.strptime(data['expiryDate'].strip(), '%Y-%m-%d').date()
        if mfg_date > exp_date: return jsonify({"success": False, "message": "Mfg date after expiry."}), 400
        if int(data['quantity']) < 0: return jsonify({"success": False, "message": "Negative quantity."}), 400
    except ValueError: return jsonify({"success": False, "message": "Invalid date or quantity format."}), 400
        
    shop_id_val = data.get('shopId', '').strip()
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        INSERT INTO medicines (barcode, medicineName, batchNo, mrp, sellingPrice, mfgDate, expiryDate, quantity, supplier, shelfNo, boxNo, shop_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get('barcode', '').strip(), data['medicineName'].strip(), data['batchNo'].strip(),
        float(data.get('mrp')) if data.get('mrp') else None, 
        float(data.get('sellingPrice')) if data.get('sellingPrice') else None,
        data['mfgDate'].strip(), data['expiryDate'].strip(), int(data['quantity']),
        data.get('supplier', '').strip(), data.get('shelfNo', '').strip(), data.get('boxNo', '').strip(),
        shop_id_val if shop_id_val else None
    ))
    new_id = cur.lastrowid; db.commit()
    new_med_row = db.execute("SELECT * FROM medicines WHERE id = ?", (new_id,)).fetchone()
    if not new_med_row: return jsonify({"success": False, "message": "Failed to retrieve after add."}), 500
    return jsonify({"success": True, "message": "Medicine added!", "medicine": {**dict(new_med_row), **get_expiry_status(new_med_row['expiryDate'])}}), 201


@app.route('/delete_medicine/<int:medicine_id>', methods=['DELETE'])
def delete_medicine_route(medicine_id):
    # ... (same as app_py_update_shopid) ...
    if not table_exists('medicines'): return jsonify({"success": False, "message": "DB not init."}), 500
    db = get_db(); cur = db.execute("DELETE FROM medicines WHERE id = ?", (medicine_id,)); db.commit()
    return jsonify({"success": True, "message": "Deleted."}) if cur.rowcount > 0 else jsonify({"success": False, "message": "Not found."}), 404


@app.route('/fetch_barcode_details', methods=['GET'])
def fetch_barcode_details_from_api_route():
    # ... (same as app_py_update_shopid) ...
    upc = request.args.get('upc', '').strip()
    if not upc: return jsonify({"success": False, "message": "UPC missing."}), 400
    api_url = f"{UPCITEMDB_TRIAL_BASE_URL}?upc={upc}"
    try:
        res = requests.get(api_url, timeout=10); res.raise_for_status(); data = res.json()
        if data.get("code") == "OK" and data.get("items") and len(data["items"]) > 0:
            item = data["items"][0]
            return jsonify({"success": True, "title": item.get("title", ""), "brand": item.get("brand", ""), "manufacturer": item.get("manufacturer", "")})
        return jsonify({"success": False, "message": data.get("message", "Product not found or API error.")})
    except requests.exceptions.RequestException as e: return jsonify({"success": False, "message": f"API request error: {e}"}), 503
    except ValueError: return jsonify({"success": False, "message": "Invalid API response."}), 500


# --- Customer Routes (customers, add_customer - same as app_py_update_shopid) ---
@app.route('/customers', methods=['GET'])
def customers():
    # ... (same as app_py_update_shopid) ...
    db = get_db()
    if not table_exists('customers'): flash("'customers' table missing.", "error"); return render_template('customers.html', customers=[]), 500
    all_cust = db.execute("SELECT id, name, phone_number, email, address, strftime('%Y-%m-%d %H:%M', registered_at) as registered_at FROM customers ORDER BY name ASC").fetchall()
    return render_template('customers.html', customers=all_cust)

@app.route('/add_customer', methods=['POST'])
def add_customer():
    # ... (same as app_py_update_shopid) ...
    if not table_exists('customers'): flash("'customers' table missing.", "error"); return redirect(url_for('customers'))
    name = request.form.get('name', '').strip(); phone = request.form.get('phone_number', '').strip()
    if not name or not phone: flash('Name and Phone are required.', 'error'); return redirect(url_for('customers'))
    db = get_db()
    try:
        db.execute("INSERT INTO customers (name, phone_number, email, address) VALUES (?, ?, ?, ?)",
                   (name, phone, request.form.get('email', '').strip() or None, request.form.get('address', '').strip() or None))
        db.commit(); flash(f'Customer "{name}" added!', 'success')
    except sqlite3.IntegrityError: db.rollback(); flash(f'Phone "{phone}" already exists.', 'error')
    except Exception as e: db.rollback(); flash(f'Error: {e}', 'error')
    return redirect(url_for('customers'))

# --- Billing Routes ---
@app.route('/billing')
def billing_page():
    """Renders the main billing page."""
    if not all(table_exists(t) for t in ['medicines', 'customers', 'bills', 'bill_items']):
        flash("One or more database tables required for billing are missing. Please initialize the database correctly.", "error")
        # return redirect(url_for('home')) # Or render billing page with a prominent error
    return render_template('billing.html')

@app.route('/search_medicines_for_billing', methods=['GET'])
def search_medicines_for_billing():
    """Searches medicines by name or their own shop_id for the billing interface."""
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify([])

    db = get_db()
    # Search by medicineName OR the medicine's specific shop_id.
    # Ensure sellingPrice is not NULL and quantity > 0 for items to be billable.
    # Only include items that are not expired.
    today_date = datetime.date.today().strftime('%Y-%m-%d')
    cur = db.execute("""
        SELECT id, medicineName, batchNo, sellingPrice, quantity, shop_id 
        FROM medicines 
        WHERE (medicineName LIKE ? OR shop_id LIKE ?) 
          AND sellingPrice IS NOT NULL 
          AND quantity > 0
          AND expiryDate >= ?
        ORDER BY medicineName
        LIMIT 10 
    """, ('%' + query + '%', '%' + query + '%', today_date)) # Added expiryDate check
    medicines = [dict(row) for row in cur.fetchall()]
    return jsonify(medicines)

@app.route('/get_customer_for_billing', methods=['GET'])
def get_customer_for_billing():
    """Fetches customer details by phone number for the billing interface."""
    phone = request.args.get('phone', '').strip()
    if not phone:
        return jsonify({"success": False, "message": "Phone number required."})
    
    db = get_db()
    customer = db.execute("SELECT id, name, phone_number, email, address FROM customers WHERE phone_number = ?", (phone,)).fetchone()
    
    if customer:
        return jsonify({"success": True, "customer": dict(customer)})
    else:
        return jsonify({"success": False, "message": "Customer not found."})

@app.route('/generate_bill', methods=['POST'])
def generate_bill_route():
    """
    Generates a new bill, saves it to the database, and updates medicine stock.
    Expects JSON payload:
    {
        "cart": [ { "medicine_id": X, "quantity_billed": Y, "price_per_unit_at_billing": Z }, ... ],
        "customer_id": A (optional, if registered),
        "customer_phone_temp": "12345" (optional, if not registered),
        "customer_name_temp": "Walk In" (optional, if not registered),
        "total_amount": B,
        "billed_from_shop_id": C (optional)
    }
    """
    data = request.get_json()
    if not data or 'cart' not in data or not data['cart'] or 'total_amount' not in data:
        return jsonify({"success": False, "message": "Invalid bill data. Cart and total amount are required."}), 400

    cart_items = data['cart']
    customer_id = data.get('customer_id')
    customer_phone_temp = data.get('customer_phone_temp')
    customer_name_temp = data.get('customer_name_temp')
    total_amount = data['total_amount']
    billed_from_shop_id = data.get('billed_from_shop_id')

    db = get_db()
    try:
        # 1. Validate stock for all items in cart
        for item_data in cart_items:
            medicine_id = item_data['medicine_id']
            quantity_billed = item_data['quantity_billed']
            
            medicine = db.execute("SELECT medicineName, quantity, expiryDate FROM medicines WHERE id = ?", (medicine_id,)).fetchone()
            if not medicine:
                db.rollback()
                return jsonify({"success": False, "message": f"Medicine with ID {medicine_id} not found."}), 400
            if medicine['quantity'] < quantity_billed:
                db.rollback()
                return jsonify({"success": False, "message": f"Insufficient stock for {medicine['medicineName']}. Available: {medicine['quantity']}."}), 400
            
            # Check for expiry
            if medicine['expiryDate'] < datetime.date.today().strftime('%Y-%m-%d'):
                db.rollback()
                return jsonify({"success": False, "message": f"Cannot bill expired medicine: {medicine['medicineName']} (Expired on: {medicine['expiryDate']})."}), 400


        # 2. Create the bill record
        bill_cur = db.cursor()
        bill_cur.execute("""
            INSERT INTO bills (customer_id, customer_phone_temp, customer_name_temp, total_amount, billed_from_shop_id)
            VALUES (?, ?, ?, ?, ?)
        """, (customer_id, customer_phone_temp, customer_name_temp, total_amount, billed_from_shop_id))
        bill_id = bill_cur.lastrowid

        # 3. Create bill items and update stock
        for item_data in cart_items:
            medicine_id = item_data['medicine_id']
            quantity_billed = item_data['quantity_billed']
            price_at_billing = item_data['price_per_unit_at_billing']
            total_for_item = quantity_billed * price_at_billing

            # Get medicine name for snapshot
            med_name_snapshot = db.execute("SELECT medicineName FROM medicines WHERE id = ?", (medicine_id,)).fetchone()['medicineName']

            db.execute("""
                INSERT INTO bill_items (bill_id, medicine_id, medicine_name_snapshot, quantity_billed, price_per_unit_at_billing, total_price_for_item)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (bill_id, medicine_id, med_name_snapshot, quantity_billed, price_at_billing, total_for_item))

            # Update stock
            db.execute("UPDATE medicines SET quantity = quantity - ? WHERE id = ?", (quantity_billed, medicine_id))

        db.commit()
        app.logger.info(f"Bill (ID: {bill_id}) generated successfully for amount {total_amount}.")
        return jsonify({"success": True, "message": "Bill generated successfully!", "bill_id": bill_id, "total_amount": total_amount})

    except sqlite3.Error as e:
        db.rollback()
        app.logger.error(f"Database error during bill generation: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"Database error: {e}"}), 500
    except Exception as e:
        db.rollback()
        app.logger.error(f"Unexpected error during bill generation: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"An unexpected error occurred: {e}"}), 500


if __name__ == '__main__':
    with app.app_context():
        if not os.path.exists(DATABASE):
            app.logger.info(f"{DATABASE} not found. Initializing database...")
            init_db()
        else:
            # Check for all tables, including new billing tables
            if not all(table_exists(t) for t in ['medicines', 'customers', 'bills', 'bill_items']):
                app.logger.warning(f"DB exists, but one or more core tables missing. Re-initializing...")
                init_db() # This will attempt to create all tables as per schema.sql
    
    app.run(debug=True, host='0.0.0.0', port=5000)

