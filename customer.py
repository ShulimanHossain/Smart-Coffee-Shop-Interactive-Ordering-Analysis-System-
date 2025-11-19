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
      

@app.route('/place_order', methods=['POST'])
def place_order():
    table_no= request.form.get('table_no')
    cart_data=request.form.get('cart_data')
    cart_items = json.loads(cart_data)
    existing_order= request.form.get('order_id')

    if existing_order :
        return add_new_item(int(existing_order),cart_items,table_no)
    
    else :
         return create_order(table_no,cart_items)
    

def create_order(table_no,cart_items):
      cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
      cursor.execute("SELECT status FROM cafe_tables WHERE table_no=%s", (table_no,))
      table = cursor.fetchone()

      if not table or table['status'] != 'Free':
          cursor.close()
          return render_template('customer/customer.html', error=f"Table {table_no} not available")
    
      cursor.execute("INSERT INTO orders (table_no, total_bill, status) VALUES (%s, %s, %s)", 
                   (table_no, 0, 'active'))
      order_id = cursor.lastrowid
      update_order_details(order_id,cart_items,cursor)
      mysql.connection.commit()
      cursor.close()
      return order_success(order_id)


def add_new_item(order_id,cart_items,table_no):
     cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
     cursor.execute("SELECT status FROM Orders WHERE order_id=%s ",(order_id,))
     order_status=cursor.fetchone()
     if not order_status or order_status['status']!='active':
          return "Order not active"
     update_order_details(order_id,cart_items,cursor)
     mysql.connection.commit()
     cursor.close()

     return order_success(order_id)


def update_order_details(order_id,cart_items,cursor):
      total_price=0
     
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
              return render_template('customer/customer.html', error=f"Not enough {ing['name']}")
          cursor.execute("INSERT INTO order_details (order_id, item_id, quantity) VALUES (%s, %s, %s)", 
                       (order_id, item_id, quantity))
          cursor.execute("SELECT price, name FROM menu WHERE item_id=%s", (item_id,))
          menu_item = cursor.fetchone()
          price = float(menu_item['price'])
          subtotal = price * quantity
          total_price += subtotal
          for ing in ingredients:
            new_stock = ing['stock'] - (ing['quantity_needed'] * quantity)
            cursor.execute("UPDATE ingredients SET quantity=%s WHERE ing_id=%s", (new_stock, ing['ing_id']))

      cursor.execute("UPDATE orders SET total_bill=total_bill + %s WHERE order_id=%s",(total_price,order_id))

def order_success(order_id):
    cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT m.name AS item_name, m.price, oi.quantity, (m.price * oi.quantity) AS subtotal
        FROM order_details oi
        JOIN menu m ON oi.item_id = m.item_id
        WHERE oi.order_id = %s
    """, (order_id,))
    ordered_items = cursor.fetchall()
    cursor.execute("SELECT total_bill, table_no FROM Orders WHERE order_id=%s", (order_id,))
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

       cursor.execute("UPDATE Orders SET payment_method=%s,payment_status='pending' WHERE order_id=%s",(method,order_id))
       mysql.connection.commit()
       cursor.close()
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
    
    cursor.execute("""SELECT menu.name, order_item.quantity, menu.price FROM OrderDetails order_item 
                   JOIN  menu ON order_item.item_id=menu.item_id WHERE order_item.order_id=%s """,(order_id,))
    items=cursor.fetchall()
    return jsonify ({"status":"Success","order":"order","items":"items"})

if __name__ =="__main__":
    app.run(debug=True)