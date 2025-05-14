# app.py
import sqlite3
import datetime
import logging
import click # For CLI commands
import os # For checking if database file exists
from flask import Flask, render_template, request, jsonify, g
import requests # For external API calls

# Attempt to import API configurations
try:
    import api
    UPCITEMDB_TRIAL_BASE_URL = api.UPCITEMDB_TRIAL_BASE_URL
    # UPCITEMDB_API_KEY = api.UPCITEMDB_API_KEY # Not strictly needed for the trial URL
except (ImportError, AttributeError) as e:
    UPCITEMDB_TRIAL_BASE_URL = "https://api.upcitemdb.com/prod/trial/lookup" # Default fallback
    logging.warning(f"Could not import UPCITEMDB_TRIAL_BASE_URL from api.py, using default. Error: {e}")

app = Flask(__name__)
DATABASE = 'inventory.db' # Database file name

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s [%(pathname)s:%(lineno)d]')

# --- Database Helper Functions ---
def get_db():
    """Connects to the specific database."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row # Access columns by name
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Closes the database again at the end of the request."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def table_exists(table_name):
    """Checks if a table exists in the database."""
    db = get_db()
    cur = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cur.fetchone() is not None

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    with app.app_context(): 
        db = get_db()
        try:
            with app.open_resource('schema.sql', mode='r') as f:
                db.cursor().executescript(f.read())
            db.commit()
            app.logger.info("Database initialized successfully using schema.sql.")
        except FileNotFoundError:
            app.logger.error("CRITICAL: schema.sql not found. Make sure it's in the same directory as app.py.")
        except Exception as e:
            app.logger.error(f"CRITICAL: Error initializing database: {e}", exc_info=True)


@app.cli.command('init-db')
def init_db_command():
    """Clear existing data and create new tables."""
    if os.path.exists(DATABASE):
        click.echo(f"WARNING: Database file '{DATABASE}' already exists. Re-initializing will clear all existing data.")
        if not click.confirm("Do you want to continue and re-initialize (this will delete existing data)?"):
            click.echo("Database initialization cancelled.")
            return
        else:
            try:
                os.remove(DATABASE) 
                click.echo(f"Removed existing database file '{DATABASE}'.")
            except OSError as e:
                click.echo(f"Error removing existing database file: {e}. Please remove it manually and try again.")
                return
    init_db()
    click.echo('Initialized the database.')

# --- Helper Functions (Expiry Status) ---
def get_expiry_status(expiry_date_str):
    if not expiry_date_str:
        return {"statusText": "N/A", "statusClass": "badge-secondary", "statusKey": "unknown"}
    today = datetime.date.today()
    try:
        expiry_date = datetime.datetime.strptime(str(expiry_date_str), '%Y-%m-%d').date()
    except ValueError:
        app.logger.warning(f"Invalid date format for expiry_date_str: {expiry_date_str}")
        return {"statusText": "Invalid Date", "statusClass": "badge-danger", "statusKey": "invalid"}
    thirty_days_from_now = today + datetime.timedelta(days=30)
    if expiry_date < today:
        return {"statusText": "Expired", "statusClass": "badge-danger", "statusKey": "expired"}
    elif expiry_date <= thirty_days_from_now:
        return {"statusText": "Expires Soon", "statusClass": "badge-warning", "statusKey": "soon"}
    else:
        return {"statusText": "Good", "statusClass": "badge-success", "statusKey": "good"}

# --- Routes ---
@app.route('/')
def index():
    db = get_db()
    if not table_exists('medicines'):
        app.logger.error("CRITICAL: 'medicines' table not found in the database.")
        app.logger.error("Please initialize the database by running 'flask init-db' in your terminal.")
        return "Error: Database not initialized. Please run 'flask init-db' in your terminal and restart the server.", 500

    cur = db.execute("SELECT * FROM medicines ORDER BY expiryDate ASC")
    medicines_from_db = cur.fetchall()
    
    medicines_with_status = []
    for row in medicines_from_db:
        med = dict(row) 
        status_info = get_expiry_status(med.get('expiryDate'))
        full_med_info = {
            "id": med.get("id"),
            "barcode": med.get("barcode", ""),
            "medicineName": med.get("medicineName", "N/A"),
            "batchNo": med.get("batchNo", "N/A"),
            "mrp": med.get("mrp"), 
            "sellingPrice": med.get("sellingPrice"), 
            "mfgDate": med.get("mfgDate", "N/A"),
            "expiryDate": med.get("expiryDate", "N/A"),
            "quantity": med.get("quantity", 0),
            "supplier": med.get("supplier", "N/A"),
            "shelfNo": med.get("shelfNo", "N/A"),
            "boxNo": med.get("boxNo", "N/A"),
            **status_info 
        }
        medicines_with_status.append(full_med_info)
    return render_template('index.html', medicines=medicines_with_status)

@app.route('/add_medicine', methods=['POST'])
def add_medicine_route():
    if not table_exists('medicines'): 
        app.logger.error("CRITICAL: 'medicines' table not found. Cannot add medicine. Run 'flask init-db'.")
        return jsonify({"success": False, "message": "Database not initialized. Please run 'flask init-db'."}), 500
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "Invalid JSON data provided."}), 400
        
        app.logger.info(f"Received data for add_medicine: {data}")

        required_fields = ['medicineName', 'batchNo', 'mfgDate', 'expiryDate', 'quantity']
        missing_or_empty_fields = [k for k in required_fields if not data.get(k) or (isinstance(data.get(k), str) and not data.get(k).strip())]
        
        if missing_or_empty_fields:
            return jsonify({"success": False, "message": f"Missing or empty required fields: {', '.join(missing_or_empty_fields)}"}), 400
        
        try:
            mfg_date_str = data['mfgDate'].strip()
            exp_date_str = data['expiryDate'].strip()
            if not mfg_date_str or not exp_date_str:
                return jsonify({"success": False, "message": "Manufacturing and Expiry dates cannot be empty."}), 400
            mfg_date = datetime.datetime.strptime(mfg_date_str, '%Y-%m-%d').date()
            exp_date = datetime.datetime.strptime(exp_date_str, '%Y-%m-%d').date()
            if mfg_date > exp_date:
                return jsonify({"success": False, "message": "Manufacturing date cannot be after expiry date."}), 400
        except ValueError:
            return jsonify({"success": False, "message": "Invalid date format. Please use YYYY-MM-DD."}), 400
        
        try:
            quantity_val = int(data['quantity'])
            if quantity_val < 0:
                return jsonify({"success": False, "message": "Quantity cannot be negative."}), 400
        except ValueError:
             return jsonify({"success": False, "message": "Invalid quantity. Please enter a whole number."}), 400

        mrp_val = data.get('mrp')
        selling_price_val = data.get('sellingPrice')

        try:
            mrp_db = float(mrp_val) if mrp_val and mrp_val.strip() else None
        except (ValueError, TypeError):
            mrp_db = None 
        
        try:
            selling_price_db = float(selling_price_val) if selling_price_val and selling_price_val.strip() else None
        except (ValueError, TypeError):
            selling_price_db = None

        db = get_db()
        cur = db.cursor()
        cur.execute("""
            INSERT INTO medicines (barcode, medicineName, batchNo, mrp, sellingPrice, mfgDate, expiryDate, quantity, supplier, shelfNo, boxNo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('barcode', '').strip(), data['medicineName'].strip(), data['batchNo'].strip(),
            mrp_db, selling_price_db, 
            mfg_date_str, exp_date_str, quantity_val,
            data.get('supplier', '').strip(), data.get('shelfNo', '').strip(), data.get('boxNo', '').strip()
        ))
        new_medicine_id = cur.lastrowid 
        db.commit()

        cur = db.execute("SELECT * FROM medicines WHERE id = ?", (new_medicine_id,))
        new_medicine_row = cur.fetchone()
        if not new_medicine_row:
             return jsonify({"success": False, "message": "Medicine added but failed to retrieve for response."}), 500

        new_medicine_dict = dict(new_medicine_row)
        status_info = get_expiry_status(new_medicine_dict['expiryDate'])
        medicine_for_response = {**new_medicine_dict, **status_info}
        
        app.logger.info(f"Added medicine: {new_medicine_dict['medicineName']} (ID: {new_medicine_id})")
        return jsonify({"success": True, "message": "Medicine added successfully!", "medicine": medicine_for_response}), 201
    
    except Exception as e:
        app.logger.error(f"Error adding medicine: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"An internal error occurred: {str(e)}"}), 500

@app.route('/delete_medicine/<int:medicine_id>', methods=['DELETE'])
def delete_medicine_route(medicine_id):
    if not table_exists('medicines'): 
        return jsonify({"success": False, "message": "Database not initialized. Please run 'flask init-db'."}), 500
    try:
        db = get_db()
        cur = db.execute("DELETE FROM medicines WHERE id = ?", (medicine_id,))
        db.commit()
        
        if cur.rowcount > 0:
            return jsonify({"success": True, "message": "Medicine deleted successfully."})
        else:
            return jsonify({"success": False, "message": "Medicine not found."}), 404
    except Exception as e:
        app.logger.error(f"Error deleting medicine with ID {medicine_id}: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"An internal error occurred: {str(e)}"}), 500


@app.route('/fetch_barcode_details', methods=['GET'])
def fetch_barcode_details_from_api_route():
    upc = request.args.get('upc')
    if not upc or not upc.strip():
        return jsonify({"success": False, "message": "UPC parameter is missing or empty."}), 400
    
    upc = upc.strip()
    api_url = f"{UPCITEMDB_TRIAL_BASE_URL}?upc={upc}"
    
    app.logger.info(f"Fetching barcode details for UPC: {upc} from {api_url}")
    response_obj = None

    try:
        response_obj = requests.get(api_url, timeout=10) 
        app.logger.info(f"UPC API response status: {response_obj.status_code}")
        response_obj.raise_for_status() 
        data = response_obj.json()
        app.logger.info(f"UPC API JSON response: {data}")
        
        if data.get("code") == "OK" and data.get("items") and len(data["items"]) > 0:
            item = data["items"][0]
            return jsonify({
                "success": True,
                "title": item.get("title", ""),
                "brand": item.get("brand", ""), 
                "manufacturer": item.get("manufacturer", "")
            })
        elif data.get("code") == "OK" and data.get("total") == 0 and not (data.get("items") and len(data["items"]) > 0) :
             return jsonify({"success": False, "message": "Product not found for this UPC."})
        elif data.get("code") == "INVALID_UPC":
            return jsonify({"success": False, "message": "Invalid UPC format according to API."})
        else:
            api_message = data.get("message", "Could not retrieve valid product details from API.")
            return jsonify({"success": False, "message": api_message})

    except requests.exceptions.HTTPError as http_err:
        error_details = "Could not retrieve error details from API response."
        if response_obj is not None:
            try:
                error_content = response_obj.json()
                error_details = error_content.get("message", response_obj.text)
            except ValueError: 
                error_details = response_obj.text
        app.logger.error(f"HTTP error occurred calling UPC API for UPC {upc}: {http_err}. Details: {error_details[:200]}", exc_info=True)
        return jsonify({"success": False, "message": f"External API Error ({response_obj.status_code if response_obj else 'N/A'}): {error_details[:200]}"}), response_obj.status_code if response_obj else 502
    except requests.exceptions.ConnectionError:
        app.logger.error(f"Connection error calling UPC API for UPC {upc}: {http_err}", exc_info=True) # Added http_err for more context if available
        return jsonify({"success": False, "message": "Could not connect to the barcode lookup service. Check network."}), 503
    except requests.exceptions.Timeout:
        app.logger.error(f"Timeout calling UPC API for UPC {upc}: {http_err}", exc_info=True) # Added http_err
        return jsonify({"success": False, "message": "Barcode lookup service timed out."}), 504
    except ValueError: # Includes JSONDecodeError from response_obj.json()
        response_text_snippet = response_obj.text[:500] if response_obj else "N/A (response object was None)"
        app.logger.error(f"Failed to decode JSON from UPC API response for UPC {upc}. Response text: {response_text_snippet}", exc_info=True)
        return jsonify({"success": False, "message": "Invalid response format from barcode lookup service."}), 500
    except requests.exceptions.RequestException as e: # Catch other requests-related errors
        app.logger.error(f"A requests-related error occurred with barcode lookup for UPC {upc}: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"An error occurred during barcode lookup: {str(e)}"}), 500
    except Exception as e: # Catch any other unexpected errors
        app.logger.error(f"An unexpected generic error occurred in fetch_barcode_details for UPC {upc}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "An unexpected internal error occurred. Please check server logs."}), 500


if __name__ == '__main__':
    db_file_exists = os.path.exists(DATABASE)
    if not db_file_exists:
        app.logger.info(f"{DATABASE} not found. Attempting to initialize database...")
        init_db() 
        if not os.path.exists(DATABASE):
             app.logger.error(f"CRITICAL: Database file '{DATABASE}' could not be created by init_db().")
             app.logger.error("Please ensure 'schema.sql' is present and run 'flask init-db' manually.")
    else: 
        with app.app_context(): 
            if not table_exists('medicines'):
                app.logger.warning(f"Database file '{DATABASE}' exists, but 'medicines' table is missing.")
                app.logger.warning("Attempting to initialize database to create missing tables...")
                init_db()
                if not table_exists('medicines'):
                    app.logger.error(f"CRITICAL: Failed to create 'medicines' table even after re-init attempt.")
                    app.logger.error("Please check 'schema.sql' and run 'flask init-db' manually.")
    
    app.run(debug=True, host='0.0.0.0', port=5000)

