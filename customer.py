from flask import Flask, render_template,request,redirect,url_for,jsonify,session,json
from flask_mysqldb import MySQL
import MySQLdb.cursors
from config import Config

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
    return render_template('customer/customer.html',menu=menu,tables=tables)  
      
@app.route('/tables')
def view_tables():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM cafe_tables")
    tables = cursor.fetchall()
    cursor.close()
    return render_template('tables.html', tables=tables)

@app.route('/place_order', methods=['POST'])
def place_order():
    table_no= request.form.get('table_no')
    cart_data=request.form.get('cart_data')
    cart_items = json.loads(cart_data)
    existing_order=request.form.get('order_id')

    cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT status FROM cafe_tables WHERE table_no=%s", (table_no,))
    table = cursor.fetchone()

    if not existing_order:
        cursor.execute("SELECT status FROM cafe_tables WHERE table_no=%s", (table_no,))
        table = cursor.fetchone()
        if not table or table['status'] != 'Free':
            cursor.close()
            return render_template('customer/customer.html', error=f"Table {table_no} not available")
   

    for item in cart_items:
        item_id = item['item_id']
        quantity = item['quantity']
        cursor.execute("""
          SELECT ingd.ing_id, ingd.name, ingd.quantity AS stock, r.quantity_needed
           FROM item_ingredients r
           JOIN ingredients ingd ON r.ing_id = ingd.ing_id
           WHERE r.item_id=%s
           """, (item_id,))
        ingredients = cursor.fetchall()
    
    
        for ing in ingredients:
            if ing['stock'] < ing['quantity_needed'] * quantity:
             cursor.close()
             return render_template('customer/customer.html', error=f"Not enough {ing['name']}")
    total_price=0
    if existing_order :
        order_id=int(existing_order)
    else :
         cursor.execute("INSERT INTO orders (table_no, total_bill, status) VALUES (%s, %s, %s)", 
                   (table_no, 0, 'active'))
         order_id = cursor.lastrowid

   

    for item in cart_items:
        item_id =item['item_id']
        quantity=item["quantity"]
        
        cursor.execute("SELECT price, name FROM menu WHERE item_id=%s", (item_id,))
        menu_item = cursor.fetchone()
        price = float(menu_item['price'])
        subtotal = price * quantity
        total_price += subtotal
        cursor.execute("INSERT INTO order_details (order_id, item_id, quantity) VALUES (%s, %s, %s)", 
                       (order_id, item['item_id'], item['quantity']))
        
        cursor.execute("""
        SELECT ingd.ing_id, ingd.quantity AS stock, r.quantity_needed
        FROM item_ingredients r
        JOIN ingredients ingd ON r.ing_id = ingd.ing_id
        WHERE r.item_id=%s
        """, (item_id,))
        ingredients = cursor.fetchall()    

        for ing in ingredients:
            new_stock = ing['stock'] - ing['quantity_needed'] * quantity
            cursor.execute("UPDATE ingredients SET quantity=%s WHERE ing_id=%s", (new_stock, ing['ing_id']))

    if existing_order:
        cursor.execute("UPDATE orders SET total_bill = total_bill + %s WHERE order_id=%s",
                       (total_price, order_id)) 
    else:
        cursor.execute("UPDATE orders SET total_bill=%s WHERE order_id=%s", (total_price, order_id))

    mysql.connection.commit()

    cursor.execute("""
        SELECT m.name AS item_name, m.price, oi.quantity, (m.price * oi.quantity) AS subtotal
        FROM order_details oi
        JOIN menu m ON oi.item_id = m.item_id
        WHERE oi.order_id = %s
    """, (order_id,))
    ordered_items = cursor.fetchall()

    cursor.execute("SELECT total_bill, table_no FROM orders WHERE order_id=%s", (order_id,))
    order_info = cursor.fetchone()
    cursor.close()

    return render_template(
        'customer/order_success.html',
        order_id=order_id,
        table_no=order_info['table_no'],
        total_price=order_info['total_bill'],
        ordered_items=ordered_items
    )

@app.route('/payment/<int:order_id>', methods=['POST','GET'])
def payment(order_id):
    cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM Orders WHERE order_id = %s',(order_id,))
    order=cursor.fetchone()
    if not order :
        return "Order not found"
    
    if request.method=="POST":
       method =request.form.get('payment_method')
       cursor.execute("UPDATE Orders SET payment_method=%s WHERE order_id=%s",(method,order_id))
       mysql.connection.commit()
       cursor.close()
       msg="Please wait, a waiter will come to receive your payment according to your selecting option"
       return render_template('payment.html',order=order,payment_done=True,payment_method=method,msg=msg)
    
    return render_template('payment.html',order=order,payment_done=False)
    


if __name__ =="__main__":
    app.run(debug=True)