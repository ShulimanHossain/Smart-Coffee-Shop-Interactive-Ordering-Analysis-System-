from flask import Flask, render_template,request,redirect,url_for,jsonify,session,json
from flask_mysqldb import MySQL
import MySQLdb.cursors
from config import Config
from datetime import datetime, timedelta
from decimal import Decimal

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key='my_key_374'
mysql=MySQL (app)

@app.route('/')
def home():
    cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT item_id, name, price FROM Menu")
    menu=cursor.fetchall() 
    cursor.execute("SELECT table_no, status FROM Cafe_tables")
    tables = cursor.fetchall()
    cursor.close()
    order_id=session.get('order_id')
    return render_template('customer.html',menu=menu,tables=tables,order_id=order_id,previous_items=[])  

def serialize_order(order):
    new_order = dict(order)  
    for key, value in new_order.items():
        if isinstance(value, (datetime, timedelta)):
            new_order[key] = str(value)
        elif isinstance(value, Decimal):
            new_order[key] = float(value)
    return new_order

@app.route('/place_order', methods=['POST'])
def place_order():
    table_no = request.form.get('table_no')
    cart_data = request.form.get('cart_data')
    cart_items = json.loads(cart_data)
    order_id = request.form.get('order_id')
    session_order_id = session.get('order_id')
    
    if order_id:
        return add_new_item(int(order_id), cart_items, table_no)

    if session_order_id:
        return add_new_item(int(session_order_id), cart_items, table_no)
    return create_order(table_no, cart_items)

def create_order(table_no, cart_items):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute("""
            UPDATE Cafe_tables SET status='Booked' WHERE table_no=%s AND status!='Booked'  """, (table_no,))
        if cursor.rowcount == 0:  
            return "Table already booked, please select another table", 409 
        cursor.execute("""
            INSERT INTO Orders (table_no, total_bill, status)  VALUES (%s, %s, 'active') """, (table_no, 0))
        order_id = cursor.lastrowid
        error_msg = update_order_details(order_id, cart_items, cursor)  
        if error_msg:
            mysql.connection.rollback()
            return error_msg, 400  

        mysql.connection.commit()
        session['order_id'] = order_id
        return redirect(url_for('continue_order', order_id=order_id))

    except Exception as e:
        mysql.connection.rollback()
        return f"DB Error: {str(e)}", 500
    finally:
        cursor.close()

def add_new_item(order_id, cart_items, table_no):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute("SELECT * FROM Orders WHERE order_id=%s", (order_id,))
        order = cursor.fetchone()
        if not order or order['status'] != 'active':
            session.pop('order_id', None)
            return redirect(url_for("home"))
        
        cursor.execute("""
            UPDATE Cafe_tables  SET status='Booked' WHERE table_no=%s AND status!='Booked'   """, (table_no,))
        error_msg = update_order_details(order_id, cart_items, cursor)
        if error_msg:
            mysql.connection.rollback()
            return error_msg, 400
        mysql.connection.commit()
        return redirect(url_for('continue_order', order_id=order_id))
    except Exception as e:
        mysql.connection.rollback()
        return f"DB Error: {str(e)}", 500
    finally:
        cursor.close()

@app.route('/continue_order/<order_id>')
def continue_order(order_id):
    if not order_id or order_id == "None":
        return redirect(url_for("home"))
    try:
        order_id = int(order_id)
    except ValueError:
        return redirect(url_for("home"))
    
    session['order_id'] = order_id
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute("SELECT * FROM Orders WHERE order_id = %s", (order_id,))
        order = cursor.fetchone()
        if not order or order['status'] != 'active':
            session.pop('order_id', None)
            return render_template(
                'customer.html',
                menu=[],
                tables=[],
                previous_items=[],
                order_id=None,
                error="Order not found or not active"
            )
        cursor.execute("""
            SELECT m.item_id, m.name, m.price, od.quantity FROM Order_details od  JOIN menu m ON od.item_id = m.item_id WHERE od.order_id = %s """, (order_id,))
        previous_items = cursor.fetchall()
        cursor.execute("SELECT item_id, name, price FROM menu")
        menu = cursor.fetchall()
        cursor.execute("SELECT table_no, status FROM Cafe_tables")
        tables = cursor.fetchall()
        return render_template(
            'customer.html',
            menu=menu,
            tables=tables,
            previous_items=previous_items,
            order_id=order_id
        )
    finally:
        cursor.close()

def update_order_details(order_id, cart_items, cursor):
    total_price = 0.0
    try:
        for item in cart_items:
            item_id = int(item['item_id'])
            quantity = int(item['quantity'])
            cursor.execute("SELECT price FROM Menu WHERE item_id=%s", (item_id,))
            menu_item = cursor.fetchone()
            if not menu_item:
                return f"Invalid item_id {item_id}"
            price = float(menu_item['price'])
            cursor.execute("""
                SELECT ing.ing_id, ing.name, ing.quantity AS stock, r.quantity_needed FROM Item_ingredients r
                JOIN Ingredients ing ON r.ing_id = ing.ing_id  WHERE r.item_id = %s
            """, (item_id,))

            ingredients = cursor.fetchall()
            for ing in ingredients:
                required = ing['quantity_needed'] * quantity
                if ing['stock'] < required:
                    return f"Not enough {ing['name']} in stock"
            cursor.execute("""  SELECT quantity FROM Order_details WHERE order_id=%s AND item_id=%s  """, (order_id, item_id))
            existing = cursor.fetchone()

            if existing:
                cursor.execute(""" UPDATE Order_details SET quantity = quantity + %s  WHERE order_id=%s AND item_id=%s """, (quantity, order_id, item_id))
            else:
                cursor.execute("""
                    INSERT INTO Order_details (order_id, item_id, quantity) VALUES (%s, %s, %s)   """, (order_id, item_id, quantity))
            total_price += price * quantity

            for ing in ingredients:
                used = ing['quantity_needed'] * quantity
                cursor.execute("""
                    UPDATE Ingredients  SET quantity = quantity - %s WHERE ing_id=%s """, (used, ing['ing_id']))
                
        cursor.execute("""
            UPDATE Orders SET total_bill = total_bill + %s WHERE order_id=%s """, (total_price, order_id))
        return None
    except Exception as e:
        return f"DB Error: {str(e)}"

@app.route('/order_success/<int:order_id>')
def order_success(order_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute("""
            SELECT m.name AS item_name, m.price, od.quantity, (m.price * od.quantity) AS subtotal
            FROM Order_details od JOIN Menu m ON od.item_id = m.item_id WHERE od.order_id = %s """, (order_id,))
        ordered_items = cursor.fetchall()
        cursor.execute("""
            SELECT total_bill, table_no, status FROM Orders WHERE order_id = %s """, (order_id,))
        order_info = cursor.fetchone()
        if not order_info:
            return render_template(
                'customer.html',
                order_id=order_id,
                table_no="Unknown",
                total_price=0,
                ordered_items=[],
                error="Order not found"
            )
        return render_template(
            'customer.html',
            order_id=order_id,
            table_no=order_info['table_no'],
            total_price=order_info['total_bill'],
            ordered_items=ordered_items
        )
    finally:
        cursor.close()

@app.route("/invoice/<int:order_id>")
def invoice(order_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute("""
            SELECT order_id, table_no, total_bill, status
            FROM Orders
            WHERE order_id = %s
        """, (order_id,))
        order = cursor.fetchone()
        if not order:
            return render_template(
                "invoice.html",
                order=None,
                items=[],
                error="Order not found"
            )
        cursor.execute("""
            SELECT od.item_id, m.name AS item_name, m.price, od.quantity,  (m.price * od.quantity) AS subtotal
            FROM Order_details od JOIN Menu m ON od.item_id = m.item_id    WHERE od.order_id = %s
        """, (order_id,))
        items = cursor.fetchall()
        return render_template("customer.html", order=order, items=items, error=None)
    finally:
        cursor.close()

@app.route('/payment/<int:order_id>', methods=['POST', 'GET'])
def payment(order_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute("SELECT * FROM Orders WHERE order_id = %s", (order_id,))
        order = cursor.fetchone()
        if not order:
            return "Order not found", 404
        if request.method == "POST":
            method = request.form.get('payment_method')
            if not method:
                return render_template('payment.html', order=order, payment_done=False, error="Select a payment method")
            cursor.execute("""
                UPDATE Orders
                SET payment_method=%s, payment_status='pending'
                WHERE order_id=%s
            """, (method, order_id))
            mysql.connection.commit()
            session.pop('order_id', None)
            msg = "Please wait... Admin will confirm your payment shortly"
            return render_template(
                'payment.html',
                order=order,
                payment_done=True,
                payment_method=method,
                msg=msg
            )
        return render_template('customer.html', order=order, payment_done=False)
    finally:
        cursor.close()
@app.route('/payment_status/<int:order_id>')
def payment_status(order_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute("SELECT payment_status FROM Orders WHERE order_id = %s", (order_id,))
        status = cursor.fetchone()
        if not status:
            return jsonify({"status": "invalid"}), 404
        return jsonify({"status": status['payment_status']})
    finally:
        cursor.close()

@app.route('/order_summary/<int:order_id>')
def order_summary(order_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute("SELECT * FROM Orders WHERE order_id = %s", (order_id,))
        order = cursor.fetchone()
        if not order:
            return jsonify({"status": "invalid"}), 404
        cursor.execute("""
            SELECT m.name, od.quantity, m.price
            FROM Order_details od JOIN Menu m ON od.item_id = m.item_id WHERE od.order_id = %s
        """, (order_id,))
        items = cursor.fetchall()
        return jsonify({
            "status": "success",
            "order": serialize_order(order),
            "items": items
        })

    finally:
        cursor.close()


if __name__ =="__main__":
    app.run(debug=True)