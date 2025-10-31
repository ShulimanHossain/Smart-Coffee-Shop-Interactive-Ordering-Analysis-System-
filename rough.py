from flask import Flask, render_template, request, jsonify, redirect, url_for
import mysql.connector
from datetime import datetime

app = Flask(__name__)

# ---------------- MYSQL CONNECTION ----------------
db = mysql.connector.connect(
    host="localhost",
    user="root",           # Your MySQL username
    password="",           # Your MySQL password
    database="smart_cafe"  # Make sure this database exists
)
cursor = db.cursor(dictionary=True)

# ----------------- ADMIN LOGIN -----------------
@app.route('/')
def home():
    return render_template('admin_login.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']

    cursor.execute("SELECT * FROM admins WHERE email=%s", (email,))
    admin = cursor.fetchone()

    if not admin:
        return render_template('admin_login.html', message="Admin not found")

    if password == admin['password']:
        return redirect(url_for('dashboard', admin_id=admin['id']))
    else:
        return render_template('admin_login.html', message="Invalid password")

# ----------------- DASHBOARD -----------------
@app.route('/admin/<int:admin_id>')
def dashboard(admin_id):
    # Fetch tables and active orders
    cursor.execute("SELECT * FROM tables")
    tables = cursor.fetchall()

    cursor.execute("SELECT * FROM orders WHERE status='active' ORDER BY timestamp DESC")
    active_orders = cursor.fetchall()

    return render_template('admin_dashboard.html', admin_id=admin_id, tables=tables, active_orders=active_orders)

# ----------------- MENU MANAGEMENT -----------------

# View menu page
@app.route('/admin/<int:admin_id>/menu')
def view_menu(admin_id):
    cursor.execute("SELECT * FROM menu")
    menu = cursor.fetchall()
    return render_template('admin_menu.html', admin_id=admin_id, menu=menu)

# Add menu item
@app.route('/admin/<int:admin_id>/menu/add', methods=['POST'])
def add_menu_item(admin_id):
    data = request.form
    name = data['name']
    price = float(data['price'])
    stock = int(data['stock'])

    cursor.execute("INSERT INTO menu (name, price, stock) VALUES (%s, %s, %s)", (name, price, stock))
    db.commit()
    return redirect(url_for('view_menu', admin_id=admin_id))

# Delete menu item
@app.route('/admin/<int:admin_id>/menu/delete/<int:item_id>', methods=['POST'])
def delete_menu_item(admin_id, item_id):
    cursor.execute("DELETE FROM menu WHERE id=%s", (item_id,))
    db.commit()
    return redirect(url_for('view_menu', admin_id=admin_id))

# Update price
@app.route('/admin/<int:admin_id>/menu/update_price', methods=['POST'])
def update_price(admin_id):
    item_id = int(request.form['item_id'])
    new_price = float(request.form['price'])
    cursor.execute("UPDATE menu SET price=%s WHERE id=%s", (new_price, item_id))
    db.commit()
    return redirect(url_for('view_menu', admin_id=admin_id))

# Update stock
@app.route('/admin/<int:admin_id>/menu/update_stock', methods=['POST'])
def update_stock(admin_id):
    item_id = int(request.form['item_id'])
    new_stock = int(request.form['stock'])
    cursor.execute("UPDATE menu SET stock=%s WHERE id=%s", (new_stock, item_id))
    db.commit()
    return redirect(url_for('view_menu', admin_id=admin_id))

# ----------------- SALES REPORT -----------------
@app.route('/admin/<int:admin_id>/sales')
def sales_report(admin_id):
    cursor.execute("SELECT * FROM orders ORDER BY timestamp DESC")
    orders = cursor.fetchall()
    total_sales = sum(order['total'] for order in orders if order['status'] == 'completed')
    return render_template('admin_sales.html', admin_id=admin_id, orders=orders, total_sales=total_sales)

# ----------------- TAKE BILL -----------------
@app.route('/admin/<int:admin_id>/take_bill/<int:order_id>', methods=['POST'])
def take_bill(admin_id, order_id):
    # Get order
    cursor.execute("SELECT * FROM orders WHERE order_id=%s", (order_id,))
    order = cursor.fetchone()
    if not order:
        return jsonify({"message": "Order not found"}), 404

    table_id = order['table_id']

    # Mark table as free
    cursor.execute("UPDATE tables SET booked=0 WHERE id=%s", (table_id,))

    # Update order status to completed
    cursor.execute("UPDATE orders SET status='completed' WHERE order_id=%s", (order_id,))
    db.commit()

    return jsonify({"message": f"Order {order_id} completed. Table {table_id} is now free."})

# ----------------- ACTIVE ORDERS -----------------
@app.route('/admin/<int:admin_id>/active_orders')
def active_orders(admin_id):
    cursor.execute("SELECT * FROM orders WHERE status='active' ORDER BY timestamp DESC")
    orders = cursor.fetchall()
    return render_template('admin_active_orders.html', admin_id=admin_id, orders=orders)

# ---------------- MAIN ----------------
if __name__ == '__main__':
    app.run(debug=True)
