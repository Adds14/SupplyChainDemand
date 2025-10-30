import mysql.connector
import datetime
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash
from mysql.connector import errorcode
import os

app = Flask(__name__)

# ##############################################################################
# CONFIGURATION
# ##############################################################################

# 1. --- !! IMPORTANT: SET A SECRET KEY !! ---
app.config['SECRET_KEY'] = '1d3b0709f18e11a14c6e911299c8558f625e149f7e834d8e8b919d7f02272e29'

# 2. --- !! IMPORTANT: DATABASE CONFIGURATION !! ---
load_dotenv()  # <-- Add this line to load the .env file

app = Flask(__name__)
# You still need a secret key for 'flash' to work
app.secret_key = os.environ.get('SECRET_KEY', 'a_fallback_secret_key_for_local_dev')

# --- THIS IS THE KEY ---
# Build your DB_CONFIG dict from the Environment Variables
# This now works for BOTH local (from .env) and Render
DB_CONFIG = {
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'host': os.environ.get('DB_HOST'),
    'database': os.environ.get('DB_NAME')
}

# --- YOUR FUNCTIONS (NO CHANGES NEEDED) ---

def get_db_connection():
    """Establishes a connection to the MySQL database."""
    try:
        # This line works perfectly now because DB_CONFIG is set from env vars
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor(dictionary=True)
        return cnx, cursor
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            flash("Error: Something is wrong with your user name or password", "danger")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            # Use .get() to safely access the db name in case it's missing
            flash(f"Error: Database '{DB_CONFIG.get('database')}' does not exist", "danger")
        else:
            flash(f"Error: {err}", "danger")
        return None, None


def close_connection(cnx, cursor):
    """Closes the database connection and cursor."""
    if cursor:
        cursor.close()
    if cnx:
        cnx.close()
@app.context_processor
def inject_datetime():
    """Makes the datetime module available to all templates."""
    return {'datetime': datetime}

# ##############################################################################
# MAIN DASHBOARD ROUTE
# ##############################################################################

@app.route('/')
def index():
    """Renders the main dashboard page."""
    return render_template('index.html')


# ##############################################################################
# CUSTOMER CRUD ROUTES
# ##############################################################################

@app.route('/customers')
def customer_list():
    """Displays a list of all customers."""
    cnx, cursor = get_db_connection()
    if cnx is None:
        return redirect(url_for('index'))

    try:
        cursor.execute("SELECT * FROM Customers ORDER BY Name")
        customers = cursor.fetchall()
        return render_template('customer_list.html', customers=customers)
    except mysql.connector.Error as err:
        flash(f"Database error: {err}", "danger")
        return redirect(url_for('index'))
    finally:
        close_connection(cnx, cursor)


@app.route('/customers/add', methods=['GET', 'POST'])
def customer_add():
    """Handles adding a new customer."""
    if request.method == 'POST':
        customer_id = request.form['customer_id']
        name = request.form['name']
        address = request.form['address']
        contact = request.form['contact']

        cnx, cursor = get_db_connection()
        if cnx is None:
            return redirect(url_for('index'))

        try:
            query = "INSERT INTO Customers (Customer_ID, Name, Address, Contact) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (customer_id, name, address, contact))
            cnx.commit()
            flash(f"Customer '{name}' added successfully!", "success")
            return redirect(url_for('customer_list'))
        except mysql.connector.Error as err:
            flash(f"Error adding customer: {err}", "danger")
            return redirect(url_for('customer_add'))
        finally:
            close_connection(cnx, cursor)

    return render_template('customer_form.html', form_title="Add New Customer")


@app.route('/customers/edit/<int:customer_id>', methods=['GET', 'POST'])
def customer_edit(customer_id):
    """Handles editing an existing customer."""
    cnx, cursor = get_db_connection()
    if cnx is None:
        return redirect(url_for('customer_list'))

    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        contact = request.form['contact']

        try:
            query = "UPDATE Customers SET Name = %s, Address = %s, Contact = %s WHERE Customer_ID = %s"
            cursor.execute(query, (name, address, contact, customer_id))
            cnx.commit()
            flash(f"Customer '{name}' updated successfully!", "success")
            return redirect(url_for('customer_list'))
        except mysql.connector.Error as err:
            flash(f"Error updating customer: {err}", "danger")
        finally:
            close_connection(cnx, cursor)

    try:
        cursor.execute("SELECT * FROM Customers WHERE Customer_ID = %s", (customer_id,))
        customer = cursor.fetchone()
        if not customer:
            flash("Customer not found!", "warning")
            return redirect(url_for('customer_list'))
        return render_template('customer_form.html', customer=customer, form_title="Edit Customer")
    except mysql.connector.Error as err:
        flash(f"Database error: {err}", "danger")
        return redirect(url_for('customer_list'))
    finally:
        if request.method == 'GET':
            close_connection(cnx, cursor)


@app.route('/customers/delete/<int:customer_id>', methods=['POST'])
def customer_delete(customer_id):
    """Handles deleting a customer."""
    cnx, cursor = get_db_connection()
    if cnx is None:
        return redirect(url_for('customer_list'))

    try:
        cursor.execute("DELETE FROM Customers WHERE Customer_ID = %s", (customer_id,))
        cnx.commit()
        flash("Customer deleted successfully!", "success")
    except mysql.connector.Error as err:
        flash(f"Error deleting customer: {err}. (Check for related orders first)", "danger")
    finally:
        close_connection(cnx, cursor)

    return redirect(url_for('customer_list'))


# ##############################################################################
# PRODUCT CRUD ROUTES
# ##############################################################################

@app.route('/products')
def product_list():
    """Displays a list of all products with their manufacturer name."""
    cnx, cursor = get_db_connection()
    if cnx is None:
        return redirect(url_for('index'))

    try:
        query = """
            SELECT p.*, m.Name as Manufacturer_Name 
            FROM Products p
            LEFT JOIN Manufacturers m ON p.Manufacturer_ID = m.Manufacturer_ID
            ORDER BY p.Name
        """
        cursor.execute(query)
        products = cursor.fetchall()
        return render_template('product_list.html', products=products)
    except mysql.connector.Error as err:
        flash(f"Database error: {err}", "danger")
        return redirect(url_for('index'))
    finally:
        close_connection(cnx, cursor)


@app.route('/products/add', methods=['GET', 'POST'])
def product_add():
    """Handles adding a new product."""
    cnx, cursor = get_db_connection()
    if cnx is None:
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            query = "INSERT INTO Products (Product_ID, Name, Description, SKU, Manufacturer_ID) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(query, (
                request.form['product_id'],
                request.form['name'],
                request.form['description'],
                request.form['sku'],
                request.form['manufacturer_id']
            ))
            cnx.commit()
            flash(f"Product '{request.form['name']}' added successfully!", "success")
            return redirect(url_for('product_list'))
        except mysql.connector.Error as err:
            flash(f"Error adding product: {err}", "danger")
            return redirect(url_for('product_add'))  # Stay on add page
        finally:
            close_connection(cnx, cursor)

    try:
        cursor.execute("SELECT Manufacturer_ID, Name FROM Manufacturers ORDER BY Name")
        manufacturers = cursor.fetchall()
        return render_template('product_form.html', manufacturers=manufacturers, form_title="Add New Product")
    except mysql.connector.Error as err:
        flash(f"Database error: {err}", "danger")
        return redirect(url_for('product_list'))
    finally:
        if request.method == 'GET':
            close_connection(cnx, cursor)


@app.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
def product_edit(product_id):
    """Handles editing an existing product."""
    cnx, cursor = get_db_connection()
    if cnx is None:
        return redirect(url_for('product_list'))

    if request.method == 'POST':
        try:
            query = """
                UPDATE Products SET 
                Name = %s, Description = %s, SKU = %s, Manufacturer_ID = %s 
                WHERE Product_ID = %s
            """
            cursor.execute(query, (
                request.form['name'],
                request.form['description'],
                request.form['sku'],
                request.form['manufacturer_id'],
                product_id
            ))
            cnx.commit()
            flash(f"Product '{request.form['name']}' updated successfully!", "success")
            return redirect(url_for('product_list'))
        except mysql.connector.Error as err:
            flash(f"Error updating product: {err}", "danger")
        finally:
            close_connection(cnx, cursor)

    try:
        cursor.execute("SELECT * FROM Products WHERE Product_ID = %s", (product_id,))
        product = cursor.fetchone()
        if not product:
            flash("Product not found!", "warning")
            return redirect(url_for('product_list'))

        cursor.execute("SELECT Manufacturer_ID, Name FROM Manufacturers ORDER BY Name")
        manufacturers = cursor.fetchall()

        return render_template('product_form.html', product=product, manufacturers=manufacturers,
                               form_title="Edit Product")
    except mysql.connector.Error as err:
        flash(f"Database error: {err}", "danger")
        return redirect(url_for('product_list'))
    finally:
        if request.method == 'GET':
            close_connection(cnx, cursor)


@app.route('/products/delete/<int:product_id>', methods=['POST'])
def product_delete(product_id):
    """Handles deleting a product."""
    cnx, cursor = get_db_connection()
    if cnx is None:
        return redirect(url_for('product_list'))

    try:
        cursor.execute("DELETE FROM Products WHERE Product_ID = %s", (product_id,))
        cnx.commit()
        flash("Product deleted successfully!", "success")
    except mysql.connector.Error as err:
        flash(f"Error deleting product: {err}. (Check for related orders first)", "danger")
    finally:
        close_connection(cnx, cursor)

    return redirect(url_for('product_list'))


# ##############################################################################
# SUPPLIER CRUD ROUTES (NEWLY ADDED)
# ##############################################################################

@app.route('/suppliers')
def supplier_list():
    """Displays a list of all suppliers."""
    cnx, cursor = get_db_connection()
    if cnx is None:
        return redirect(url_for('index'))

    try:
        cursor.execute("SELECT * FROM Suppliers ORDER BY Name")
        suppliers = cursor.fetchall()
        return render_template('supplier_list.html', suppliers=suppliers)
    except mysql.connector.Error as err:
        flash(f"Database error: {err}", "danger")
        return redirect(url_for('index'))
    finally:
        close_connection(cnx, cursor)


@app.route('/suppliers/add', methods=['GET', 'POST'])
def supplier_add():
    """Handles adding a new supplier."""
    if request.method == 'POST':
        cnx, cursor = get_db_connection()
        if cnx is None: return redirect(url_for('index'))
        try:
            query = "INSERT INTO Suppliers (Supplier_ID, Name, Contact, Address) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (
                request.form['supplier_id'],
                request.form['name'],
                request.form['contact'],
                request.form['address']
            ))
            cnx.commit()
            flash(f"Supplier '{request.form['name']}' added successfully!", "success")
            return redirect(url_for('supplier_list'))
        except mysql.connector.Error as err:
            flash(f"Error adding supplier: {err}", "danger")
            return redirect(url_for('supplier_add'))
        finally:
            close_connection(cnx, cursor)

    return render_template('supplier_form.html', form_title="Add New Supplier")


@app.route('/suppliers/edit/<int:supplier_id>', methods=['GET', 'POST'])
def supplier_edit(supplier_id):
    """Handles editing an existing supplier."""
    cnx, cursor = get_db_connection()
    if cnx is None: return redirect(url_for('supplier_list'))

    if request.method == 'POST':
        try:
            query = "UPDATE Suppliers SET Name = %s, Contact = %s, Address = %s WHERE Supplier_ID = %s"
            cursor.execute(query, (
                request.form['name'],
                request.form['contact'],
                request.form['address'],
                supplier_id
            ))
            cnx.commit()
            flash(f"Supplier '{request.form['name']}' updated successfully!", "success")
            return redirect(url_for('supplier_list'))
        except mysql.connector.Error as err:
            flash(f"Error updating supplier: {err}", "danger")
        finally:
            close_connection(cnx, cursor)

    try:
        cursor.execute("SELECT * FROM Suppliers WHERE Supplier_ID = %s", (supplier_id,))
        supplier = cursor.fetchone()
        if not supplier:
            flash("Supplier not found!", "warning")
            return redirect(url_for('supplier_list'))
        return render_template('supplier_form.html', supplier=supplier, form_title="Edit Supplier")
    except mysql.connector.Error as err:
        flash(f"Database error: {err}", "danger")
        return redirect(url_for('supplier_list'))
    finally:
        if request.method == 'GET':
            close_connection(cnx, cursor)


@app.route('/suppliers/delete/<int:supplier_id>', methods=['POST'])
def supplier_delete(supplier_id):
    """Handles deleting a supplier."""
    cnx, cursor = get_db_connection()
    if cnx is None: return redirect(url_for('supplier_list'))
    try:
        cursor.execute("DELETE FROM Suppliers WHERE Supplier_ID = %s", (supplier_id,))
        cnx.commit()
        flash("Supplier deleted successfully!", "success")
    except mysql.connector.Error as err:
        flash(f"Error deleting supplier: {err}. (Check for related manufacturers first)", "danger")
    finally:
        close_connection(cnx, cursor)
    return redirect(url_for('supplier_list'))


# ##############################################################################
# MANUFACTURER CRUD ROUTES (NEWLY ADDED)
# ##############################################################################

@app.route('/manufacturers')
def manufacturer_list():
    """Displays a list of all manufacturers."""
    cnx, cursor = get_db_connection()
    if cnx is None: return redirect(url_for('index'))
    try:
        cursor.execute("SELECT * FROM Manufacturers ORDER BY Name")
        manufacturers = cursor.fetchall()
        return render_template('manufacturer_list.html', manufacturers=manufacturers)
    except mysql.connector.Error as err:
        flash(f"Database error: {err}", "danger")
        return redirect(url_for('index'))
    finally:
        close_connection(cnx, cursor)


@app.route('/manufacturers/add', methods=['GET', 'POST'])
def manufacturer_add():
    """Handles adding a new manufacturer."""
    if request.method == 'POST':
        cnx, cursor = get_db_connection()
        if cnx is None: return redirect(url_for('index'))
        try:
            query = "INSERT INTO Manufacturers (Manufacturer_ID, Name, Contact, Address) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (
                request.form['manufacturer_id'],
                request.form['name'],
                request.form['contact'],
                request.form['address']
            ))
            cnx.commit()
            flash(f"Manufacturer '{request.form['name']}' added successfully!", "success")
            return redirect(url_for('manufacturer_list'))
        except mysql.connector.Error as err:
            flash(f"Error adding manufacturer: {err}", "danger")
            return redirect(url_for('manufacturer_add'))
        finally:
            close_connection(cnx, cursor)

    return render_template('manufacturer_form.html', form_title="Add New Manufacturer")


@app.route('/manufacturers/edit/<int:manufacturer_id>', methods=['GET', 'POST'])
def manufacturer_edit(manufacturer_id):
    """Handles editing an existing manufacturer."""
    cnx, cursor = get_db_connection()
    if cnx is None: return redirect(url_for('manufacturer_list'))

    if request.method == 'POST':
        try:
            query = "UPDATE Manufacturers SET Name = %s, Contact = %s, Address = %s WHERE Manufacturer_ID = %s"
            cursor.execute(query, (
                request.form['name'],
                request.form['contact'],
                request.form['address'],
                manufacturer_id
            ))
            cnx.commit()
            flash(f"Manufacturer '{request.form['name']}' updated successfully!", "success")
            return redirect(url_for('manufacturer_list'))
        except mysql.connector.Error as err:
            flash(f"Error updating manufacturer: {err}", "danger")
        finally:
            close_connection(cnx, cursor)

    try:
        cursor.execute("SELECT * FROM Manufacturers WHERE Manufacturer_ID = %s", (manufacturer_id,))
        manufacturer = cursor.fetchone()
        if not manufacturer:
            flash("Manufacturer not found!", "warning")
            return redirect(url_for('manufacturer_list'))
        return render_template('manufacturer_form.html', manufacturer=manufacturer, form_title="Edit Manufacturer")
    except mysql.connector.Error as err:
        flash(f"Database error: {err}", "danger")
        return redirect(url_for('manufacturer_list'))
    finally:
        if request.method == 'GET':
            close_connection(cnx, cursor)


@app.route('/manufacturers/delete/<int:manufacturer_id>', methods=['POST'])
def manufacturer_delete(manufacturer_id):
    """Handles deleting a manufacturer."""
    cnx, cursor = get_db_connection()
    if cnx is None: return redirect(url_for('manufacturer_list'))
    try:
        cursor.execute("DELETE FROM Manufacturers WHERE Manufacturer_ID = %s", (manufacturer_id,))
        cnx.commit()
        flash("Manufacturer deleted successfully!", "success")
    except mysql.connector.Error as err:
        flash(f"Error deleting manufacturer: {err}. (Check for related products/suppliers first)", "danger")
    finally:
        close_connection(cnx, cursor)
    return redirect(url_for('manufacturer_list'))


# ##############################################################################
# WAREHOUSE CRUD ROUTES (NEWLY ADDED)
# ##############################################################################

@app.route('/warehouses')
def warehouse_list():
    """Displays a list of all warehouses."""
    cnx, cursor = get_db_connection()
    if cnx is None: return redirect(url_for('index'))
    try:
        cursor.execute("SELECT * FROM Warehouses ORDER BY Name")
        warehouses = cursor.fetchall()
        return render_template('warehouse_list.html', warehouses=warehouses)
    except mysql.connector.Error as err:
        flash(f"Database error: {err}", "danger")
        return redirect(url_for('index'))
    finally:
        close_connection(cnx, cursor)


@app.route('/warehouses/add', methods=['GET', 'POST'])
def warehouse_add():
    """Handles adding a new warehouse."""
    if request.method == 'POST':
        cnx, cursor = get_db_connection()
        if cnx is None: return redirect(url_for('index'))
        try:
            query = "INSERT INTO Warehouses (Warehouse_ID, Name, Location, Capacity) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (
                request.form['warehouse_id'],
                request.form['name'],
                request.form['location'],
                request.form['capacity']
            ))
            cnx.commit()
            flash(f"Warehouse '{request.form['name']}' added successfully!", "success")
            return redirect(url_for('warehouse_list'))
        except mysql.connector.Error as err:
            flash(f"Error adding warehouse: {err}", "danger")
            return redirect(url_for('warehouse_add'))
        finally:
            close_connection(cnx, cursor)

    return render_template('warehouse_form.html', form_title="Add New Warehouse")


@app.route('/warehouses/edit/<int:warehouse_id>', methods=['GET', 'POST'])
def warehouse_edit(warehouse_id):
    """Handles editing an existing warehouse."""
    cnx, cursor = get_db_connection()
    if cnx is None: return redirect(url_for('warehouse_list'))

    if request.method == 'POST':
        try:
            query = "UPDATE Warehouses SET Name = %s, Location = %s, Capacity = %s WHERE Warehouse_ID = %s"
            cursor.execute(query, (
                request.form['name'],
                request.form['location'],
                request.form['capacity'],
                warehouse_id
            ))
            cnx.commit()
            flash(f"Warehouse '{request.form['name']}' updated successfully!", "success")
            return redirect(url_for('warehouse_list'))
        except mysql.connector.Error as err:
            flash(f"Error updating warehouse: {err}", "danger")
        finally:
            close_connection(cnx, cursor)

    try:
        cursor.execute("SELECT * FROM Warehouses WHERE Warehouse_ID = %s", (warehouse_id,))
        warehouse = cursor.fetchone()
        if not warehouse:
            flash("Warehouse not found!", "warning")
            return redirect(url_for('warehouse_list'))
        return render_template('warehouse_form.html', warehouse=warehouse, form_title="Edit Warehouse")
    except mysql.connector.Error as err:
        flash(f"Database error: {err}", "danger")
        return redirect(url_for('warehouse_list'))
    finally:
        if request.method == 'GET':
            close_connection(cnx, cursor)


@app.route('/warehouses/delete/<int:warehouse_id>', methods=['POST'])
def warehouse_delete(warehouse_id):
    """Handles deleting a warehouse."""
    cnx, cursor = get_db_connection()
    if cnx is None: return redirect(url_for('warehouse_list'))
    try:
        cursor.execute("DELETE FROM Warehouses WHERE Warehouse_ID = %s", (warehouse_id,))
        cnx.commit()
        flash("Warehouse deleted successfully!", "success")
    except mysql.connector.Error as err:
        flash(f"Error deleting warehouse: {err}. (Check for inventory first)", "danger")
    finally:
        close_connection(cnx, cursor)
    return redirect(url_for('warehouse_list'))


# ##############################################################################
# VEHICLE CRUD ROUTES (NEWLY ADDED)
# ##############################################################################

@app.route('/vehicles')
def vehicle_list():
    """Displays a list of all vehicles."""
    cnx, cursor = get_db_connection()
    if cnx is None: return redirect(url_for('index'))
    try:
        cursor.execute("SELECT * FROM Vehicles ORDER BY Type, License_Plate")
        vehicles = cursor.fetchall()
        return render_template('vehicle_list.html', vehicles=vehicles)
    except mysql.connector.Error as err:
        flash(f"Database error: {err}", "danger")
        return redirect(url_for('index'))
    finally:
        close_connection(cnx, cursor)


@app.route('/vehicles/add', methods=['GET', 'POST'])
def vehicle_add():
    """Handles adding a new vehicle."""
    if request.method == 'POST':
        cnx, cursor = get_db_connection()
        if cnx is None: return redirect(url_for('index'))
        try:
            query = "INSERT INTO Vehicles (Vehicle_ID, Type, License_Plate, Capacity, Status) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(query, (
                request.form['vehicle_id'],
                request.form['type'],
                request.form['license_plate'],
                request.form['capacity'],
                request.form['status']
            ))
            cnx.commit()
            flash(f"Vehicle '{request.form['license_plate']}' added successfully!", "success")
            return redirect(url_for('vehicle_list'))
        except mysql.connector.Error as err:
            flash(f"Error adding vehicle: {err}", "danger")
            return redirect(url_for('vehicle_add'))
        finally:
            close_connection(cnx, cursor)

    return render_template('vehicle_form.html', form_title="Add New Vehicle")


@app.route('/vehicles/edit/<int:vehicle_id>', methods=['GET', 'POST'])
def vehicle_edit(vehicle_id):
    """Handles editing an existing vehicle."""
    cnx, cursor = get_db_connection()
    if cnx is None: return redirect(url_for('vehicle_list'))

    if request.method == 'POST':
        try:
            query = "UPDATE Vehicles SET Type = %s, License_Plate = %s, Capacity = %s, Status = %s WHERE Vehicle_ID = %s"
            cursor.execute(query, (
                request.form['type'],
                request.form['license_plate'],
                request.form['capacity'],
                request.form['status'],
                vehicle_id
            ))
            cnx.commit()
            flash(f"Vehicle '{request.form['license_plate']}' updated successfully!", "success")
            return redirect(url_for('vehicle_list'))
        except mysql.connector.Error as err:
            flash(f"Error updating vehicle: {err}", "danger")
        finally:
            close_connection(cnx, cursor)

    try:
        cursor.execute("SELECT * FROM Vehicles WHERE Vehicle_ID = %s", (vehicle_id,))
        vehicle = cursor.fetchone()
        if not vehicle:
            flash("Vehicle not found!", "warning")
            return redirect(url_for('vehicle_list'))
        return render_template('vehicle_form.html', vehicle=vehicle, form_title="Edit Vehicle")
    except mysql.connector.Error as err:
        flash(f"Database error: {err}", "danger")
        return redirect(url_for('vehicle_list'))
    finally:
        if request.method == 'GET':
            close_connection(cnx, cursor)


@app.route('/vehicles/delete/<int:vehicle_id>', methods=['POST'])
def vehicle_delete(vehicle_id):
    """Handles deleting a vehicle."""
    cnx, cursor = get_db_connection()
    if cnx is None: return redirect(url_for('vehicle_list'))
    try:
        cursor.execute("DELETE FROM Vehicles WHERE Vehicle_ID = %s", (vehicle_id,))
        cnx.commit()
        flash("Vehicle deleted successfully!", "success")
    except mysql.connector.Error as err:
        flash(f"Error deleting vehicle: {err}. (Check for related shipments first)", "danger")
    finally:
        close_connection(cnx, cursor)
    return redirect(url_for('vehicle_list'))


# ##############################################################################
# ORDER & SHIPMENT VIEW ROUTES
# ##############################################################################

@app.route('/orders')
def order_list():
    """Displays a list of all orders with customer and invoice info."""
    cnx, cursor = get_db_connection()
    if cnx is None:
        return redirect(url_for('index'))

    try:
        query = """
            SELECT o.Order_ID, o.Date, o.Status, c.Name as Customer_Name,
                   i.Amount, i.Status as Invoice_Status
            FROM Orders o
            LEFT JOIN Customers c ON o.Customer_ID = c.Customer_ID
            LEFT JOIN Invoices i ON o.Order_ID = i.Order_ID
            ORDER BY o.Date DESC
        """
        cursor.execute(query)
        orders = cursor.fetchall()
        return render_template('order_list.html', orders=orders)
    except mysql.connector.Error as err:
        flash(f"Database error: {err}", "danger")
        return redirect(url_for('index'))
    finally:
        close_connection(cnx, cursor)


@app.route('/orders/<int:order_id>')
def order_detail(order_id):
    """Shows the full details for a single order."""
    cnx, cursor = get_db_connection()
    if cnx is None:
        return redirect(url_for('order_list'))

    try:
        data = {}

        # 1. Get Order, Customer, and Invoice Info
        query_order = """
            SELECT o.*, c.Name as Customer_Name, c.Address as Customer_Address, c.Contact as Customer_Contact,
                   i.Invoice_ID, i.Amount, i.Due_Date, i.Status as Invoice_Status
            FROM Orders o
            LEFT JOIN Customers c ON o.Customer_ID = c.Customer_ID
            LEFT JOIN Invoices i ON o.Order_ID = i.Order_ID
            WHERE o.Order_ID = %s
        """
        cursor.execute(query_order, (order_id,))
        data['order'] = cursor.fetchone()

        if not data['order']:
            flash("Order not found!", "warning")
            return redirect(url_for('order_list'))

        # 2. Get Order Items (Products in the order)
        query_items = """
            SELECT oi.Quantity, p.Product_ID, p.Name, p.SKU
            FROM order_items oi
            JOIN Products p ON oi.Product_ID = p.Product_ID
            WHERE oi.Order_ID = %s
        """
        cursor.execute(query_items, (order_id,))
        data['items'] = cursor.fetchall()

        # 3. Get Shipment Info
        query_shipment = """
            SELECT s.*, v.Type as Vehicle_Type, v.License_Plate
            FROM Shipments s
            LEFT JOIN Vehicles v ON s.Vehicle_ID = v.Vehicle_ID
            WHERE s.Order_ID = %s
        """
        cursor.execute(query_shipment, (order_id,))
        data['shipments'] = cursor.fetchall()

        return render_template('order_detail.html', **data)

    except mysql.connector.Error as err:
        flash(f"Database error: {err}", "danger")
        return redirect(url_for('order_list'))
    finally:
        close_connection(cnx, cursor)


# ##############################################################################
# ADVANCED REPORTS ROUTES
# ##############################################################################

@app.route('/reports')
def reports_index():
    """Shows the main reports page with a list of available reports."""
    report_list = [
        {'id': 'top_customers', 'name': 'Top 5 Customers by Purchase Value'},
        {'id': 'low_stock', 'name': 'Low-Stock Products (Stock < 100)'},
        {'id': 'delayed_shipments', 'name': 'Delayed Shipments (En Route past Arrival Date)'},
        {'id': 'warehouse_revenue', 'name': 'Total Paid Revenue Per Warehouse'},
        {'id': 'overdue_invoices', 'name': 'Overdue Pending Invoices'},
        {'id': 'product_suppliers', 'name': 'All Products and Their Suppliers'},
        {'id': 'vehicle_usage', 'name': 'Vehicle Shipment Frequency'},
        {'id': 'popular_products', 'name': 'Most Popular Products (by Quantity Ordered)'},
        {'id': 'avg_ship_duration', 'name': 'Average Shipment Duration'},
        {'id': 'manufacturer_products', 'name': 'Product Count by Manufacturer'},
    ]
    return render_template('reports.html', report_list=report_list)


@app.route('/reports/<string:report_name>')
def run_report(report_name):
    """Runs and displays a specific advanced report."""
    cnx, cursor = get_db_connection()
    if cnx is None:
        return redirect(url_for('reports_index'))

    query = ""
    report_title = ""

    try:
        # Match the report_name to the corresponding SQL query from your presentation
        if report_name == 'top_customers':
            report_title = "Top 5 Customers by Purchase Value"
            query = """
                SELECT c.Name, SUM(i.Amount) AS total_spent
                FROM Customers c
                JOIN Orders o ON c.Customer_ID = o.Customer_ID
                JOIN Invoices i ON o.Order_ID = i.Order_ID
                WHERE i.Status = 'Paid'
                GROUP BY c.Name
                ORDER BY total_spent DESC
                LIMIT 5
            """

        elif report_name == 'low_stock':
            report_title = "Low-Stock Products (Stock < 100)"
            query = """
                SELECT p.Name, w.Name as warehouse_name, wi.Stock
                FROM warehouse_inventory wi
                JOIN Products p ON wi.Product_ID = p.Product_ID
                JOIN Warehouses w ON wi.Warehouse_ID = w.Warehouse_ID
                WHERE wi.Stock < 100
                ORDER BY wi.Stock ASC
            """

        elif report_name == 'delayed_shipments':
            report_title = "Delayed Shipments (En Route past Arrival Date)"
            query = """
                SELECT s.Shipment_ID, o.Order_ID, s.Destination, s.Departure_Date, s.Arrival_Date
                FROM Shipments s
                JOIN Orders o ON s.Order_ID = o.Order_ID
                WHERE s.Status = 'En Route' AND s.Arrival_Date < CURDATE()
            """

        elif report_name == 'warehouse_revenue':
            report_title = "Total Paid Revenue Per Warehouse"
            query = """
                SELECT w.Name AS warehouse_name, SUM(i.Amount) AS total_revenue
                FROM Invoices i
                JOIN Orders o ON i.Order_ID = o.Order_ID
                JOIN order_items oi ON o.Order_ID = oi.Order_ID
                JOIN warehouse_inventory wi ON oi.Product_ID = wi.Product_ID
                JOIN Warehouses w ON wi.Warehouse_ID = w.Warehouse_ID
                WHERE i.Status = 'Paid'
                GROUP BY w.Name
                ORDER BY total_revenue DESC
            """

        elif report_name == 'overdue_invoices':
            report_title = "Overdue Pending Invoices"
            query = """
                SELECT Invoice_ID, Order_ID, Amount, Due_Date
                FROM Invoices
                WHERE Status = 'Pending' AND Due_Date < CURDATE()
                ORDER BY Due_Date ASC
            """

        elif report_name == 'product_suppliers':
            report_title = "All Products and Their Suppliers"
            query = """
                SELECT p.Name AS product_name, m.Name AS manufacturer_name, s.Name AS supplier_name
                FROM Products p
                JOIN Manufacturers m ON p.Manufacturer_ID = m.Manufacturer_ID
                JOIN manufacturer_suppliers ms ON m.Manufacturer_ID = ms.Manufacturer_ID
                JOIN Suppliers s ON ms.Supplier_ID = s.Supplier_ID
                ORDER BY p.Name
            """

        elif report_name == 'vehicle_usage':
            report_title = "Vehicle Shipment Frequency"
            query = """
                SELECT v.Vehicle_ID, v.Type, v.License_Plate, COUNT(s.Shipment_ID) AS number_of_shipments
                FROM Vehicles v
                LEFT JOIN Shipments s ON v.Vehicle_ID = s.Vehicle_ID
                GROUP BY v.Vehicle_ID, v.Type, v.License_Plate
                ORDER BY number_of_shipments DESC
            """

        elif report_name == 'popular_products':
            report_title = "Most Popular Products (by Quantity Ordered)"
            query = """
                SELECT p.Name, SUM(oi.Quantity) AS total_quantity_ordered
                FROM order_items oi
                JOIN Products p ON oi.Product_ID = p.Product_ID
                GROUP BY p.Name
                ORDER BY total_quantity_ordered DESC
            """

        elif report_name == 'avg_ship_duration':
            report_title = "Average Shipment Duration"
            query = """
                SELECT AVG(DATEDIFF(Arrival_Date, Departure_Date)) AS average_shipping_days
                FROM Shipments
                WHERE Arrival_Date IS NOT NULL AND Departure_Date IS NOT NULL
            """

        elif report_name == 'manufacturer_products':
            report_title = "Product Count by Manufacturer"
            query = """
                SELECT m.Name, COUNT(p.Product_ID) AS number_of_products
                FROM Manufacturers m
                JOIN Products p ON m.Manufacturer_ID = p.Manufacturer_ID
                GROUP BY m.Name
                ORDER BY number_of_products DESC
            """

        else:
            flash("Unknown report selected", "warning")
            return redirect(url_for('reports_index'))

        cursor.execute(query)
        report_data = cursor.fetchall()

        report_headers = [i[0] for i in cursor.description] if report_data else []

        # Special case for AVG
        if report_name == 'avg_ship_duration' and report_data:
            avg_days = report_data[0]['average_shipping_days']
            report_data = [{'average_shipping_days': f"{float(avg_days):.2f} days"}]

        return render_template(
            'report_detail.html',
            report_title=report_title,
            report_headers=report_headers,
            report_data=report_data
        )

    except mysql.connector.Error as err:
        flash(f"Database error running report: {err}", "danger")
        return redirect(url_for('reports_index'))
    finally:
        close_connection(cnx, cursor)


# ##############################################################################
# APPLICATION RUNNER
# ##############################################################################

if __name__ == '__main__':
    app.run(debug=True)
