from flask import Flask, render_template,request,redirect,url_for,jsonify,session
from flask_mysqldb import MySQL
import MySQLdb.cursors
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key='my_key_374'
mysql=MySQL (app)

@app.route('/')
def home():
    return render_template('customer.html')  

@app.route('/api/menu',methods=['GET'])
def get_menu(): 
    cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT item_id, name, price FROM menu")
    menu=cursor.fetchall()
    cursor.close()
    return jsonify(menu)
                    
@app.route('/api/table_status/<int:table_no>', methods=['GET'])
def table_status(table_no):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute("SELECT status FROM tables WHERE table_no=%s", (table_no,))
        table = cursor.fetchone()
        if not table:
            return jsonify({'error': 'Table not found'}), 404
        return jsonify({'status': table['status']})         
    finally:
        cursor.close()
        
@app.route('/api/place_order',methods=['POST'])
def place_order():
    order=request.json
    table_no=order.get("table_number")
    order_item=order.get("order_item",[])

    if not table_no or not order_item:
        return jsonify({'error': 'Missing table number or items'}), 400
    
    cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try: 
        cursor.execute("SELECT status FROM  tables WHERE table_no=%s",(table_no))
        table=cursor.fetchone()
        if not table:
            return jsonify({"error":" Invalid table number" })
        if table ['status']!='Free':
             return jsonify({"error":f"Table{table_no} is already {table['status']}"})
        
        cursor.execute("UPDATE tables SRT status=%s WHERE table_no=%s", ("Not Free",table_no))

        total_price=0

        for item in order_item:
            cursor.execute("""
                SELECT ingd.ing_id, ingd.name, ingd.quantity AS stock, r.quantity_needed
                FROM item_ingredients r
                JOIN ingredients ingd ON r.ing_id = ingd.ing_id
                WHERE r.item_id = %s
            """, (item['item_id'],))
            ingredients = cursor.fetchall()
            
            for ing in ingredients:
                required = ing['quantity_needed'] * item['quantity']
                if ing['stock'] < required:
                    return jsonify({'error': f"Not enough {ing['name']} for item {item['item_id']}"}), 400
                
        for item in order_item:
            
            cursor.execute("SELECT price FROM menu WHERE item_id=%s", (item['item_id'],))
            result = cursor.fetchone()
            total_price += result['price'] * item['quantity']

            
            cursor.execute("""
                SELECT ingd.ing_id, ingd.quantity AS stock, r.quantity_needed
                FROM item_ingredients r
                JOIN ingredients ingd ON r.ing_id = ingd.ing_id
                WHERE r.item_id = %s
            """, (item['item_id'],))
            ingredients = cursor.fetchall()
            for ing in ingredients:
                new_stock = ing['stock'] - ing['quantity_needed'] * item['quantity']
                cursor.execute("UPDATE ingredients SET quantity=%s WHERE ing_id=%s",
                               (new_stock, ing['ing_id']))
                
        cursor.execute("""
        INSERT INTO orders (table_no, total_price)
        VALUES (%s, %s)
        """, (table_no, total_price))
        order_id = cursor.lastrowid

        for item in order_item:
            cursor.execute("""
                INSERT INTO order_items (order_id, item_id, quantity)
                VALUES (%s, %s, %s)
            """, (order_id, item['item_id'], item['quantity']))
        mysql.connection.commit()
        return jsonify({'message': 'Order placed successfully', 'order_id': order_id}), 201

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()

if __name__ =="__main__":
    app.run(debug=True)