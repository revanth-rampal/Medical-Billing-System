# app.py
import sqlite3
import datetime
import logging
import click 
import os 
from flask import Flask, render_template, request, jsonify, g, redirect, url_for, flash, session
from functools import wraps 
import requests
import qrcode # For QR code generation
import io # To handle image in memory
import base64 # To encode image for HTML display
import urllib.parse # For encoding UPI URL parameters

# --- API Configuration ---
try:
    import api 
    UPCITEMDB_TRIAL_BASE_URL = api.UPCITEMDB_TRIAL_BASE_URL
except (ImportError, AttributeError) as e:
    UPCITEMDB_TRIAL_BASE_URL = "https://api.upcitemdb.com/prod/trial/lookup" 
    logging.warning(f"Could not import UPCITEMDB_TRIAL_BASE_URL from api.py, using default. Error: {e}")

# --- Flask App Initialization ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24) 
DATABASE = 'inventory.db'

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s [%(pathname)s:%(lineno)d]')

# --- Database Helper Functions ---
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
            required_tables = ['medicines', 'customers', 'bills', 'bill_items', 'app_settings']
            for table in required_tables:
                if not table_exists(table):
                    app.logger.error(f"CRITICAL: '{table}' table NOT created after init_db.")
                else:
                    # Ensure default app_settings are present if table was just created
                    if table == 'app_settings':
                        cur = db.cursor()
                        cur.execute("INSERT OR IGNORE INTO app_settings (setting_key, setting_value) VALUES (?, ?)", ('upi_id', ''))
                        cur.execute("INSERT OR IGNORE INTO app_settings (setting_key, setting_value) VALUES (?, ?)", ('payee_name', ''))
                        db.commit()
                        app.logger.info("Ensured default app_settings (upi_id, payee_name) are present.")

        except FileNotFoundError:
            app.logger.error("CRITICAL: schema.sql not found. Database cannot be initialized.")
        except Exception as e:
            app.logger.error(f"CRITICAL: Error initializing database: {e}", exc_info=True)

@app.cli.command('init-db')
def init_db_command():
    if os.path.exists(DATABASE):
        click.echo(f"WARNING: Database file '{DATABASE}' already exists. Re-initializing will clear ALL data.")
        if not click.confirm("Do you want to continue and re-initialize the database?"):
            click.echo("Database initialization cancelled.")
            return
        try:
            os.remove(DATABASE) 
            click.echo(f"Removed existing database '{DATABASE}'.")
        except OSError as e:
            click.echo(f"Error removing existing database: {e}. Please remove it manually and try again.")
            return
    init_db()
    click.echo('Initialized the database.')

# --- Utility Functions ---
def get_expiry_status(expiry_date_str):
    if not expiry_date_str:
        return {"statusText": "N/A", "statusClass": "badge-secondary", "statusKey": "unknown"}
    today = datetime.date.today()
    try:
        expiry_date = datetime.datetime.strptime(str(expiry_date_str), '%Y-%m-%d').date()
    except ValueError:
        return {"statusText": "Invalid Date", "statusClass": "badge-danger", "statusKey": "invalid"}
    if expiry_date < today:
        return {"statusText": "Expired", "statusClass": "badge-danger", "statusKey": "expired"}
    elif expiry_date <= (today + datetime.timedelta(days=30)): 
        return {"statusText": "Expires Soon", "statusClass": "badge-warning", "statusKey": "soon"}
    else:
        return {"statusText": "Good", "statusClass": "badge-success", "statusKey": "good"}

def get_app_setting(key):
    db = get_db()
    if not table_exists('app_settings'):
        app.logger.warning("app_settings table does not exist. Returning None.")
        return None
    row = db.execute("SELECT setting_value FROM app_settings WHERE setting_key = ?", (key,)).fetchone()
    return row['setting_value'] if row else None

def update_app_setting(key, value):
    db = get_db()
    if not table_exists('app_settings'):
        app.logger.error("Cannot update setting: app_settings table does not exist.")
        return False
    try:
        db.execute("INSERT OR REPLACE INTO app_settings (setting_key, setting_value) VALUES (?, ?)", (key, value))
        db.commit()
        return True
    except sqlite3.Error as e:
        app.logger.error(f"Database error updating app setting '{key}': {e}")
        db.rollback()
        return False

# --- Context Processors ---
@app.context_processor
def inject_now():
    return {'SCRIPT_START_TIME': datetime.datetime.utcnow()}

@app.context_processor
def inject_user_role():
    if 'user_id' in session:
        return {'user_role': session.get('role')}
    return {}

# --- Decorators ---
def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'info')
                return redirect(url_for('login', next=request.url))
            if role and session.get('role') != role:
                flash(f'You do not have permission to access this page. Required role: {role}.', 'error')
                if session.get('role') == 'admin':
                    return redirect(url_for('admin_home'))
                elif session.get('role') == 'employee':
                    return redirect(url_for('home'))
                return redirect(url_for('login')) 
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- Authentication Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session: 
        if session.get('role') == 'admin':
            return redirect(url_for('admin_home'))
        return redirect(url_for('home'))

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        password = request.form.get('password')
        if user_id == 'admin' and password == 'admin':
            session['user_id'] = user_id
            session['role'] = 'admin'
            flash('Logged in successfully as Admin!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('admin_home'))
        elif user_id == 'PharmaEmployee' and password == 'pharma':
            session['user_id'] = user_id
            session['role'] = 'employee'
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('home'))
        else:
            flash('Invalid User ID or Password. Please try again.', 'error')
            return render_template('login.html'), 401 
    return render_template('login.html')

@app.route('/logout')
@login_required() 
def logout():
    session.pop('user_id', None)
    session.pop('role', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

# --- Main Application Routes ---
@app.route('/')
@login_required() 
def index_redirect():
    if session.get('role') == 'admin':
        return redirect(url_for('admin_home'))
    elif session.get('role') == 'employee':
        return redirect(url_for('home'))
    else:
        flash('Login required.', 'error')
        return redirect(url_for('login'))

@app.route('/admin/home') 
@login_required(role='admin') 
def admin_home():
    upi_id = get_app_setting('upi_id')
    payee_name = get_app_setting('payee_name')
    return render_template('admin_home.html', upi_settings={'upi_id': upi_id, 'payee_name': payee_name})

@app.route('/admin/upi_settings', methods=['POST'])
@login_required(role='admin')
def admin_upi_settings():
    upi_id = request.form.get('upi_id', '').strip()
    payee_name = request.form.get('payee_name', '').strip()

    if not upi_id or not payee_name:
        flash('Both UPI ID and Payee Name are required.', 'error')
    else:
        update_app_setting('upi_id', upi_id)
        update_app_setting('payee_name', payee_name)
        flash('UPI settings updated successfully!', 'success')
    return redirect(url_for('admin_home'))


@app.route('/home')
@login_required() 
def home():
    if session.get('role') == 'admin':
         pass 
    return render_template('home.html')


@app.route('/inventory')
@login_required()
def inventory():
    db = get_db()
    if not table_exists('medicines'):
        flash("The 'medicines' table is missing. Please initialize the database.", "error")
        return render_template('inventory.html', medicines=[]), 500
    cur = db.execute("SELECT id, barcode, medicineName, batchNo, mrp, sellingPrice, mfgDate, expiryDate, quantity, supplier, shelfNo, boxNo, shop_id FROM medicines ORDER BY expiryDate ASC")
    medicines_from_db = cur.fetchall()
    medicines_with_status = []
    for row in medicines_from_db:
        med_dict = dict(row) 
        status_info = get_expiry_status(med_dict.get('expiryDate'))
        full_med_info = {**med_dict, **status_info}
        medicines_with_status.append(full_med_info)
    return render_template('inventory.html', medicines=medicines_with_status)

@app.route('/add_medicine', methods=['POST'])
@login_required()
def add_medicine_route():
    if not table_exists('medicines'):
        return jsonify({"success": False, "message": "Database not initialized: 'medicines' table missing."}), 500
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Invalid JSON data received."}), 400
    required_fields = ['medicineName', 'batchNo', 'mfgDate', 'expiryDate', 'quantity']
    missing_fields = [field for field in required_fields if not data.get(field) or (isinstance(data.get(field), str) and not data.get(field).strip())]
    if missing_fields:
        return jsonify({"success": False, "message": f"Missing required fields: {', '.join(missing_fields)}."}), 400
    try:
        mfg_date = datetime.datetime.strptime(data['mfgDate'].strip(), '%Y-%m-%d').date()
        expiry_date = datetime.datetime.strptime(data['expiryDate'].strip(), '%Y-%m-%d').date()
        if mfg_date > expiry_date:
            return jsonify({"success": False, "message": "Manufacturing date cannot be after expiry date."}), 400
        quantity = int(data['quantity'])
        if quantity < 0:
            return jsonify({"success": False, "message": "Quantity cannot be negative."}), 400
        mrp = float(data.get('mrp')) if data.get('mrp') else None
        if mrp is not None and mrp < 0:
            return jsonify({"success": False, "message": "MRP cannot be negative."}), 400
        selling_price = float(data.get('sellingPrice')) if data.get('sellingPrice') else None
        if selling_price is not None and selling_price < 0:
            return jsonify({"success": False, "message": "Selling Price cannot be negative."}), 400
    except ValueError:
        return jsonify({"success": False, "message": "Invalid data format for date, quantity, or price."}), 400
    shop_id_val = data.get('shopId', '').strip()
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("""
            INSERT INTO medicines (barcode, medicineName, batchNo, mrp, sellingPrice, mfgDate, expiryDate, quantity, supplier, shelfNo, boxNo, shop_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('barcode', '').strip(), data['medicineName'].strip(), data['batchNo'].strip(),
            mrp, selling_price,
            data['mfgDate'].strip(), data['expiryDate'].strip(), quantity,
            data.get('supplier', '').strip(), data.get('shelfNo', '').strip(), data.get('boxNo', '').strip(),
            shop_id_val if shop_id_val else None 
        ))
        new_medicine_id = cur.lastrowid
        db.commit()
        new_med_row = db.execute("SELECT * FROM medicines WHERE id = ?", (new_medicine_id,)).fetchone()
        if not new_med_row:
             app.logger.error(f"Failed to retrieve newly added medicine with ID: {new_medicine_id}")
             return jsonify({"success": False, "message": "Medicine added but failed to retrieve details."}), 500
        medicine_details = {**dict(new_med_row), **get_expiry_status(new_med_row['expiryDate'])}
        return jsonify({"success": True, "message": "Medicine added successfully!", "medicine": medicine_details}), 201
    except sqlite3.Error as e:
        db.rollback()
        app.logger.error(f"Database error on adding medicine: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"Database error: {e}"}), 500

@app.route('/delete_medicine/<int:medicine_id>', methods=['DELETE'])
@login_required()
def delete_medicine_route(medicine_id):
    if not table_exists('medicines'):
        return jsonify({"success": False, "message": "Database not initialized."}), 500
    db = get_db()
    try:
        cur = db.execute("DELETE FROM medicines WHERE id = ?", (medicine_id,))
        db.commit()
        if cur.rowcount > 0:
            return jsonify({"success": True, "message": "Medicine deleted successfully."})
        else:
            return jsonify({"success": False, "message": "Medicine not found or already deleted."}), 404
    except sqlite3.Error as e:
        db.rollback()
        app.logger.error(f"Database error on deleting medicine ID {medicine_id}: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"Database error: {e}"}), 500

@app.route('/fetch_barcode_details', methods=['GET'])
@login_required()
def fetch_barcode_details_from_api_route():
    upc = request.args.get('upc', '').strip()
    if not upc:
        return jsonify({"success": False, "message": "UPC (barcode) parameter is missing."}), 400
    api_url = f"{UPCITEMDB_TRIAL_BASE_URL}?upc={upc}"
    app.logger.info(f"Fetching barcode details for UPC: {upc} from {api_url}")
    try:
        response = requests.get(api_url, timeout=10) 
        response.raise_for_status() 
        data = response.json()
        if data.get("code") == "OK" and data.get("items") and len(data["items"]) > 0:
            item = data["items"][0]
            app.logger.info(f"Successfully fetched details for UPC {upc}: Title - {item.get('title')}")
            return jsonify({"success": True, "title": item.get("title", ""),"brand": item.get("brand", ""),"manufacturer": item.get("manufacturer", "")})
        else:
            app.logger.warning(f"API call for UPC {upc} did not return 'OK' or no items found. Response: {data.get('message', 'No message')}")
            return jsonify({"success": False, "message": data.get("message", "Product not found or API error.")})
    except requests.exceptions.Timeout:
        app.logger.error(f"Timeout error when fetching barcode details for UPC: {upc}", exc_info=True)
        return jsonify({"success": False, "message": "API request timed out. Please try again."}), 504 
    except requests.exceptions.RequestException as e:
        app.logger.error(f"API request error for UPC {upc}: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"API request error: {e}"}), 503 
    except ValueError: 
        app.logger.error(f"Invalid JSON response from API for UPC {upc}", exc_info=True)
        return jsonify({"success": False, "message": "Invalid API response format."}), 500

# --- Customer Management Routes ---
@app.route('/customers', methods=['GET'])
@login_required()
def customers():
    db = get_db()
    if not table_exists('customers'):
        flash("The 'customers' table is missing. Please initialize the database.", "error")
        return render_template('customers.html', customers=[]), 500
    all_customers = db.execute("SELECT id, name, phone_number, email, address, strftime('%Y-%m-%d %H:%M', registered_at) as registered_at FROM customers ORDER BY name ASC").fetchall()
    return render_template('customers.html', customers=all_customers)

@app.route('/add_customer', methods=['POST'])
@login_required()
def add_customer():
    if not table_exists('customers'):
        flash("Database not initialized: 'customers' table missing.", "error")
        return redirect(url_for('customers'))
    name = request.form.get('name', '').strip()
    phone_number = request.form.get('phone_number', '').strip()
    email = request.form.get('email', '').strip() or None 
    address = request.form.get('address', '').strip() or None 
    if not name or not phone_number:
        flash('Customer Name and Phone Number are required fields.', 'error')
        return redirect(url_for('customers'))
    db = get_db()
    try:
        db.execute("INSERT INTO customers (name, phone_number, email, address) VALUES (?, ?, ?, ?)", (name, phone_number, email, address))
        db.commit()
        flash(f'Customer "{name}" added successfully!', 'success')
    except sqlite3.IntegrityError: 
        db.rollback()
        flash(f'Error: Phone number "{phone_number}" already exists for another customer.', 'error')
    except sqlite3.Error as e:
        db.rollback()
        app.logger.error(f"Database error on adding customer: {e}", exc_info=True)
        flash(f'Database error occurred: {e}', 'error')
    return redirect(url_for('customers'))

# --- Billing Routes ---
@app.route('/billing')
@login_required()
def billing_page():
    required_billing_tables = ['medicines', 'customers', 'bills', 'bill_items', 'app_settings']
    for table_name in required_billing_tables:
        if not table_exists(table_name):
            flash(f"Database error: The '{table_name}' table required for billing is missing. Please initialize the database.", "error")
            if session.get('role') == 'admin': return redirect(url_for('admin_home'))
            return redirect(url_for('home'))
    return render_template('billing.html')

@app.route('/search_medicines_for_billing', methods=['GET'])
@login_required()
def search_medicines_for_billing():
    query = request.args.get('query', '').strip()
    if not query: return jsonify([]) 
    db = get_db()
    today_date_str = datetime.date.today().strftime('%Y-%m-%d')
    try:
        cur = db.execute("""
            SELECT id, medicineName, batchNo, sellingPrice, quantity, shop_id 
            FROM medicines 
            WHERE (LOWER(medicineName) LIKE LOWER(?) OR LOWER(shop_id) LIKE LOWER(?))
              AND sellingPrice IS NOT NULL AND sellingPrice > 0 AND quantity > 0 AND expiryDate >= ?
            ORDER BY medicineName LIMIT 10 
        """, (f'%{query}%', f'%{query}%', today_date_str))
        medicines = [dict(row) for row in cur.fetchall()]
        return jsonify(medicines)
    except sqlite3.Error as e:
        app.logger.error(f"Database error searching medicines for billing (query: {query}): {e}", exc_info=True)
        return jsonify({"error": "Database search error"}), 500

@app.route('/get_customer_for_billing', methods=['GET'])
@login_required()
def get_customer_for_billing():
    phone = request.args.get('phone', '').strip()
    if not phone: return jsonify({"success": False, "message": "Phone number is required."}), 400
    db = get_db()
    try:
        customer_row = db.execute("SELECT id, name, phone_number, email, address FROM customers WHERE phone_number = ?", (phone,)).fetchone()
        if customer_row: return jsonify({"success": True, "customer": dict(customer_row)})
        else: return jsonify({"success": False, "message": "Customer not found with this phone number."})
    except sqlite3.Error as e:
        app.logger.error(f"Database error fetching customer for billing (phone: {phone}): {e}", exc_info=True)
        return jsonify({"success": False, "message": f"Database error: {e}"}), 500

def generate_upi_qr_code(upi_id, payee_name, amount, bill_id):
    """Generates a UPI QR code image as a base64 string."""
    if not upi_id or not payee_name:
        app.logger.warning("UPI ID or Payee Name is not configured. Cannot generate QR code.")
        return None, "UPI details not configured by admin."
    
    formatted_amount = f"{float(amount):.2f}"

    params = {
        'pa': upi_id,
        'pn': urllib.parse.quote(payee_name), 
        'am': formatted_amount,
        'tn': urllib.parse.quote(f"Bill ID: {bill_id} - {payee_name}"), 
        'tr': urllib.parse.quote(f"PHARMABILL{bill_id}") 
    }
    upi_url = f"upi://pay?{urllib.parse.urlencode(params)}"
    app.logger.info(f"Generated UPI URL: {upi_url}")

    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(upi_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
    return img_str, upi_url


@app.route('/generate_bill', methods=['POST'])
@login_required()
def generate_bill_route():
    data = request.get_json()
    if not data or 'cart' not in data or not isinstance(data['cart'], list) or not data['cart'] or 'total_amount' not in data:
        return jsonify({"success": False, "message": "Invalid bill data. Cart items and total amount are required."}), 400
    
    cart_items = data['cart']
    total_amount_from_request = data['total_amount']
    
    try:
        total_amount_from_request = float(total_amount_from_request)
        if total_amount_from_request < 0:
             return jsonify({"success": False, "message": "Total amount cannot be negative."}), 400
    except ValueError:
        return jsonify({"success": False, "message": "Invalid total amount format."}), 400

    customer_id = data.get('customer_id') # Will be None if key not present
    
    # Safely get and strip optional string values from JSON
    customer_phone_temp_raw = data.get('customer_phone_temp')
    customer_phone_temp = customer_phone_temp_raw.strip() if isinstance(customer_phone_temp_raw, str) else None
    
    customer_name_temp_raw = data.get('customer_name_temp')
    customer_name_temp = customer_name_temp_raw.strip() if isinstance(customer_name_temp_raw, str) else None
    
    billed_from_shop_id_raw = data.get('billed_from_shop_id')
    billed_from_shop_id = billed_from_shop_id_raw.strip() if isinstance(billed_from_shop_id_raw, str) else None

    db = get_db()
    calculated_total = 0 
    try:
        db.execute("BEGIN TRANSACTION")
        today_date_str = datetime.date.today().strftime('%Y-%m-%d')
        for item_data in cart_items:
            medicine_id = item_data.get('medicine_id')
            quantity_billed = item_data.get('quantity_billed')
            price_at_billing_client = item_data.get('price_per_unit_at_billing') 
            if not all([isinstance(medicine_id, int), isinstance(quantity_billed, int), quantity_billed > 0, 
                        isinstance(price_at_billing_client, (int, float)), price_at_billing_client >= 0]):
                db.rollback(); return jsonify({"success": False, "message": "Invalid item data in cart (ID, quantity, or price)."}), 400
            medicine = db.execute("SELECT medicineName, quantity, expiryDate, sellingPrice FROM medicines WHERE id = ?", (medicine_id,)).fetchone()
            if not medicine: db.rollback(); return jsonify({"success": False, "message": f"Medicine with ID {medicine_id} not found."}), 400
            if medicine['quantity'] < quantity_billed: db.rollback(); return jsonify({"success": False, "message": f"Insufficient stock for {medicine['medicineName']}. Available: {medicine['quantity']}, Requested: {quantity_billed}."}), 400
            if medicine['expiryDate'] < today_date_str: db.rollback(); return jsonify({"success": False, "message": f"Cannot bill expired medicine: {medicine['medicineName']} (Expired on: {medicine['expiryDate']})."}), 400
            if medicine['sellingPrice'] is None: db.rollback(); return jsonify({"success": False, "message": f"Selling price not set for {medicine['medicineName']}."}), 400
            price_at_billing_server = medicine['sellingPrice']
            calculated_total += quantity_billed * price_at_billing_server
            item_data['price_per_unit_at_billing'] = price_at_billing_server 
            item_data['medicine_name_snapshot'] = medicine['medicineName'] 
        
        if abs(calculated_total - total_amount_from_request) > 0.01: 
            app.logger.warning(f"Bill total mismatch. Client: {total_amount_from_request}, Server: {calculated_total}. Using server total.")
        final_total_amount = calculated_total 
        
        bill_cur = db.cursor()
        bill_cur.execute("""
            INSERT INTO bills (customer_id, customer_phone_temp, customer_name_temp, total_amount, billed_from_shop_id, bill_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (customer_id, customer_phone_temp, customer_name_temp, final_total_amount, billed_from_shop_id, datetime.datetime.now()))
        bill_id = bill_cur.lastrowid
        
        for item_data in cart_items:
            db.execute("""
                INSERT INTO bill_items (bill_id, medicine_id, medicine_name_snapshot, quantity_billed, price_per_unit_at_billing, total_price_for_item)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (bill_id, item_data['medicine_id'], item_data['medicine_name_snapshot'], item_data['quantity_billed'], item_data['price_per_unit_at_billing'], item_data['quantity_billed'] * item_data['price_per_unit_at_billing']))
            # Update stock for the current medicine item
            db.execute("UPDATE medicines SET quantity = quantity - ? WHERE id = ?", (item_data['quantity_billed'], item_data['medicine_id']))
        
        upi_id_setting = get_app_setting('upi_id')
        payee_name_setting = get_app_setting('payee_name')
        qr_code_base64, upi_payment_url = None, None
        upi_url_message = "Scan QR to pay. Ensure amount is correct."

        if upi_id_setting and payee_name_setting:
            qr_code_base64, upi_payment_url = generate_upi_qr_code(upi_id_setting, payee_name_setting, final_total_amount, bill_id)
            if not qr_code_base64:
                upi_url_message = "Could not generate QR code. UPI details might be missing or invalid."
        else:
            upi_url_message = "UPI payment is not configured by admin."
            app.logger.warning(f"UPI QR code not generated for Bill ID {bill_id} as UPI settings are incomplete.")

        db.commit() 
        app.logger.info(f"Bill (ID: {bill_id}) generated by user {session.get('user_id')} for amount {final_total_amount:.2f}.")
        return jsonify({
            "success": True, 
            "message": "Bill generated successfully!", 
            "bill_id": bill_id, 
            "total_amount": final_total_amount,
            "qr_code_image": qr_code_base64, 
            "payee_name": payee_name_setting,
            "upi_url_message": upi_url_message
        })
    except sqlite3.Error as e:
        db.rollback(); app.logger.error(f"Database error during bill generation: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"Database error: {e}"}), 500
    except Exception as e:
        db.rollback(); app.logger.error(f"Unexpected error during bill generation: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"An unexpected error occurred: {e}"}), 500

# --- Main Execution ---
if __name__ == '__main__':
    with app.app_context():
        db_exists = os.path.exists(DATABASE)
        if not db_exists:
            app.logger.info(f"Database file '{DATABASE}' not found. Initializing database...")
            init_db()
        else:
            app.logger.info(f"Database file '{DATABASE}' found.")
            required_tables = ['medicines', 'customers', 'bills', 'bill_items', 'app_settings'] 
            all_tables_exist = all(table_exists(t) for t in required_tables)
            if not all_tables_exist:
                app.logger.warning(f"Database '{DATABASE}' exists, but one or more required tables are missing. Re-initializing...")
                init_db() 
    app.run(debug=True, host='0.0.0.0', port=5000)

