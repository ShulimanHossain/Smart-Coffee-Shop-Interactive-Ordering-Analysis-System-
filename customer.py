from flask import Flask, render_template,request,redirect,url_for,jsonify,session,json
from flask_mysqldb import MySQL
import MySQLdb.cursors
from config import Config
from datetime import datetime, timedelta

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key='my_key_374'
mysql=MySQL (app)

@app.route('/')
def home():
    
    cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT item_id, name, price FROM menu")
    menu=cursor.fetchall() 
    cursor.execute("SELECT table_no, status FROM cafe_tables")
    tables = cursor.fetchall()
    cursor.close()
    order_id=session.get('order_id')
    return render_template('customer/customer.html',menu=menu,tables=tables,order_id=order_id,previous_items=[])  
    

def serialize_order(order):
    new_order = dict(order)  # convert MySQL dict to regular dict
    for key, value in new_order.items():
        if isinstance(value, (datetime, timedelta)):
            new_order[key] = str(value)  # convert to string
    return new_order

@app.route('/place_order', methods=['POST'])
def place_order():

    table_no = request.form.get('table_no')
    cart_data = request.form.get('cart_data')
    cart_items = json.loads(cart_data)
    order_id = request.form.get('order_id')

    # Determine whether this is new order or existing order
    if order_id:
        order_id_to_use = order_id
    elif 'order_id' in session:
        order_id_to_use = session['order_id']
    else:
        order_id_to_use = None

    # Continue existing order
    if order_id_to_use:
        try:
            order_id_to_use = int(order_id_to_use)
        except:
            pass
        return add_new_item(order_id_to_use, cart_items, table_no)

    # Create new order
    return create_order(table_no, cart_items)

    
@app.route('/update_cart', methods=['POST'])
def update_cart():
    data = request.get_json()

    session['cart'] = data.get('cart', [])
    session.modified = True

    return jsonify({"status": "success"})

def create_order(table_no, cart_items):

    cursor = mysql.connection.cursor()

    # Mark table as BOOKED
    cursor.execute(
        "UPDATE cafe_tables SET status = 'Booked' WHERE table_no = %s",
        (table_no,)
    )

    # Create order
    cursor.execute("""
        INSERT INTO Orders (table_no, total_bill, status)
        VALUES (%s, %s, 'active')
    """, (table_no, 0))

    order_id = cursor.lastrowid

    # Add items
    total = 0
    for item in cart_items:
        cursor.execute("""
            INSERT INTO Order_details (order_id, item_id, quantity)
            VALUES (%s, %s, %s)
        """, (order_id, item['item_id'], item['quantity']))

        total += float(item['price']) * item['quantity']

    # Update total price
    cursor.execute("""
        UPDATE Orders SET total_bill = %s WHERE order_id = %s
    """, (total, order_id))

    mysql.connection.commit()
    cursor.close()

    session['order_id'] = order_id

    return redirect(url_for('continue_order', order_id=order_id))


def add_new_item(order_id, cart_items, table_no):

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Verify the existing order is active
    cursor.execute("SELECT * FROM Orders WHERE order_id = %s", (order_id,))
    order = cursor.fetchone()

    if not order:
       
        return redirect(url_for("home"))

    if order['status'] != 'active':
        
        return redirect(url_for("home"))

    # Ensure table is booked
    cursor.execute(
        "UPDATE cafe_tables SET status = 'Booked' WHERE table_no = %s",
        (table_no,)
    )

    # Insert new items
    total = float(order['total_bill'])

    for item in cart_items:
        cursor.execute("""
            INSERT INTO Order_details (order_id, item_id, quantity)
            VALUES (%s, %s, %s)
        """, (order_id, item['item_id'], item['quantity']))

        total += float(item['price']) * item['quantity']

    # Update bill
    cursor.execute("""
        UPDATE Orders SET total_bill = %s WHERE order_id = %s
    """, (total, order_id))

    mysql.connection.commit()
    cursor.close()

    return redirect(url_for('continue_order', order_id=order_id))

@app.route('/continue_order/<order_id>')
def continue_order(order_id):
    if not order_id or order_id == "None":
        return redirect(url_for("home"))

    # store in session
    session['order_id'] = int(order_id)

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch order
    cursor.execute("SELECT * FROM Orders WHERE order_id = %s", (order_id,))
    order = cursor.fetchone()
    if not order or order['status'] != 'active':
        return render_template('customer/customer.html',
                               menu=[],
                               tables=[],
                               previous_items=[],
                               order_id=None,
                               error="Order not found or not active")

    # Fetch cart items
    cursor.execute("""
        SELECT m.item_id, m.name, m.price, od.quantity
        FROM Order_details od
        JOIN menu m ON od.item_id = m.item_id
        WHERE od.order_id = %s
    """, (order_id,))
    previous_items = cursor.fetchall()

    # Fetch menu and tables
    cursor.execute("SELECT item_id, name, price FROM menu")
    menu = cursor.fetchall()
    cursor.execute("SELECT table_no, status FROM cafe_tables")
    tables = cursor.fetchall()
    cursor.close()

    return render_template('customer/customer.html',
                           menu=menu,
                           tables=tables,
                           previous_items=previous_items,
                           order_id=order_id)

def update_order_details(order_id, cart_items, cursor):
    total_price = 0.0

    try:
        for item in cart_items:
            item_id = item['item_id']
            quantity = int(item['quantity'])

            cursor.execute("""
                SELECT ingd.ing_id, ingd.name, ingd.quantity AS stock, r.quantity_needed
                FROM item_ingredients r
                JOIN ingredients ingd ON r.ing_id = ingd.ing_id
                WHERE r.item_id=%s
            """, (item_id,))
            ingredients = cursor.fetchall()

            for ing in ingredients:
                if ing['stock'] < ing['quantity_needed'] * quantity:
                    return f"Not enough {ing['name']}"

            cursor.execute("INSERT INTO Order_details (order_id, item_id, quantity) VALUES (%s, %s, %s)",
                           (order_id, item_id, quantity))

            cursor.execute("SELECT price, name FROM menu WHERE item_id=%s", (item_id,))
            menu_item = cursor.fetchone()
            price = float(menu_item['price'])
            subtotal = price * quantity
            total_price += subtotal

            for ing in ingredients:
                new_stock = ing['stock'] - (ing['quantity_needed'] * quantity)
                cursor.execute("UPDATE ingredients SET quantity=%s WHERE ing_id=%s",
                               (new_stock, ing['ing_id']))

        cursor.execute("UPDATE Orders SET total_bill=total_bill + %s WHERE order_id=%s", (total_price, order_id))
        return None

    except Exception as e:
        
        return f"DB Error: {str(e)}"

@app.route('/order_success/<int:order_id>')
def order_success(order_id):
    cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT m.name AS item_name, m.price, oi.quantity, (m.price * oi.quantity) AS subtotal
        FROM Order_details oi
        JOIN menu m ON oi.item_id = m.item_id
        WHERE oi.order_id = %s
    """, (order_id,))
    ordered_items = cursor.fetchall()
    cursor.execute("SELECT total_bill, table_no FROM Orders WHERE order_id=%s", (order_id,))
    order_info = cursor.fetchone()
    cursor.close()
    
    if not order_info:
        return render_template( 'customer/order_success.html',
        order_id=order_id,
        table_no="Unknown Table number",
        total_price=0,
        ordered_items=[],error="Order not found")

    return render_template(
        'customer/order_success.html',
        order_id=order_id,
        table_no=order_info['table_no'],
        total_price=order_info['total_bill'],
        ordered_items=ordered_items
    )


@app.route("/invoice/<int:order_id>")
def invoice(order_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM orders WHERE order_id = %s", (order_id,))
    order = cur.fetchone()

    cur.execute("SELECT * FROM order_details WHERE order_id = %s", (order_id,))
    items = cur.fetchall()
    cur.close()

    return render_template("invoice.html", order=order, items=items)


@app.route('/payment/<int:order_id>', methods=['POST','GET'])
def payment(order_id):
    cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM Orders WHERE order_id = %s',(order_id,))
    order=cursor.fetchone()
    if not order :
        return "Order not found"
    
    if request.method=="POST":
       
       method =request.form.get('payment_method')

       cursor.execute("UPDATE Orders SET payment_method=%s,payment_status='pending' WHERE order_id=%s",(method,order_id))
       mysql.connection.commit()
       cursor.close()

       session.pop('order_id',None)
       msg="Please wait.... Admin will confirm your payment shortly"
       return render_template('payment.html',order=order,payment_done=True,payment_method=method,msg=msg)
    cursor.close()
    return render_template('payment.html',order=order,payment_done=False)
  
@app.route('/payment_status/<int:order_id>')
def payment_status(order_id):
    cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT payment_status FROM Orders WHERE order_id = %s',(order_id,))
    status=cursor.fetchone()
    cursor.close()

    if not status:
        return "invalid"

    return status['payment_status']

@app.route('/order_summary/<int:order_id>')
def order_summary(order_id):
    cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM Orders WHERE order_id = %s',(order_id,))
    order=cursor.fetchone()
    
    if not order:
        return jsonify({"status": "invalid"})
    
    cursor.execute("""SELECT menu.name, order_item.quantity, menu.price FROM Order_details order_item 
                   JOIN  menu ON order_item.item_id=menu.item_id WHERE order_item.order_id=%s """,(order_id,))
    items=cursor.fetchall()
    return jsonify({
    "status": "Success",
    "order": serialize_order(order),
    "items": items
    })

if __name__ =="__main__":
    app.run(debug=True)