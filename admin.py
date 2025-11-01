from flask import Flask, render_template,request,redirect,url_for,jsonify,session
from flask_mysqldb import MySQL
import MySQLdb.cursors
from config import Config
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key='my_key_374'
mysql=MySQL (app)


@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        userid=request.form['admin_id']
        password=request.form['password']
    cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    admin=cursor.fetchone()
    if not admin :
        return render_template('login.html', message="Admin not found")
    if password== admin[password]:
        return redirect(url_for('admin_dashboard',admin_id=userid))
    else :
        return render_template('login.html',message="Invalid password")

@app.route('/admin/<int:admin_id>')
def admin_dashboard(admin_id):
    cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT *  FROM tables")
    table=cursor.fetchall()
    cursor.execute("SELECT * FROM orders WHERE status ='active' ORDER BY timestamp DESC")
    active_order =cursor.fetchall()
    return render_template('admin_dashboard.html',admin_id=admin_id,tables=table,active_order=active_order)

@app.route('/admin<int:admin_id>/menu')
def view_menu(admin_id):
    cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM Menu")
    menu=cursor.fetchall()
    return render_template('admin_dashboard.html',admin_id=admin_id,menu=menu)

@app.route('/admin/<int:admin_id>/add_item', methods=['POST'])
def add_item(admin_id):
    name = request.form.get('name')
    price = float(request.form.get('price'))
    cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    message=''
    cursor.execute("INSERT INTO menu (name, price) VALUES (%s, %s)", (name, price))
    mysql.connection.commit()
    item_id = cursor.lastrowid 

    ingredient_names = request.form.getlist('ingredient_name[]')
    ingredient_quantities = request.form.getlist('ingredient_quantity[]')

    for ing_name, qty in zip(ingredient_names, ingredient_quantities):

        cursor.execute("SELECT ing_id FROM ingredients WHERE name = %s", (ing_name,))
        result = cursor.fetchone()

        if result:
            ing_id = result['ing_id']
        else:
           
            cursor.execute("INSERT INTO ingredients (name, stock) VALUES (%s, %s)", (ing_name, 0))
            mysql.connection.commit()
            ing_id = cursor.lastrowid
            message="Item added successfully"

        cursor.execute(" INSERT INTO item_ingredients (item_id, ing_id, quantity_needed) VALUES (%s, %s, %s) ", (item_id, ing_id, qty))
        mysql.connection.commit()
        message="Item added successfully"
    
    return redirect(url_for('admin_dashboard.html',action='add_item',message=message, admin_id=admin_id))


@app.route('/admin/<int:admin_id>/menu/delete_menu/<int:item_id>',methods=['POST','GET'])
def delete_menu(admin_id,item_id):
    if request.method=='POST':
        message=''
        item_id=request.form['item_id']
        cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        try:
            cursor.execute('DELETE FROM menu WHERE item_id=%s',(item_id,))
            mysql.connection.commit()
            message="Item deleted successfully"
        except Exception as e:
            mysql.connection.rollback()
            print("Error deleting:", e)
    cursor.execute("SELECT item_id,name FROM Menu")
    menu=cursor.fetchall()
    cursor.close()
    return render_template('delete_menu.html',action='delete_menu',message=message)

@app.route('/admin/menu/change_price/<int:item_id>',methods=['POST','GET'])
def change_price():
    
    message=''
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    if request.method=='POST':
           item_id=request.form['item_id']
           newprice=request.form['newprice']
           try:
            cursor.execute('UPDATE menu SET price =%s WHERE item_id=%s ',(newprice,item_id))
            mysql.connection.commit()
            message="successfully changed price"
           except Exception as e:
            mysql.connection.rollback()
            print("Error deleting:", e)  
    cursor.execute("SELECT item_id,name FROM Menu")
    menu=cursor.fetchall()
    cursor.close()
    return render_template('change_price.html',action='change_price',menu=menu,message=message)

@app.route('/admin/updatestock', methods=['GET','POST'])
def updatestock():
      message=''
      if request.method=='POST':
           ing_id=request.form['ing_id']
           new_quantity=request.form['new_quantity']
           cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
           try: 
            cursor.execute("UPDATE Ingredients SET quantity=%s WHERE  ing_id=%s",(new_quantity,ing_id))
            mysql.connection.commit()
            message="successfully update stock"
           except Exception as e:
            mysql.connection.rollback()
            print("Error deleting:", e)  
      cursor.execute("SELECT ing_id,name, quantity FROM Ingredients")
      ingredients=cursor.fetchall()
      cursor.close()
      return render_template('update_stock.html',action='updatestock',ingredients=ingredients,message=message)

@app.route('/api/admin/order',methods=['GET'])
def view_order():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM Orders WHERE status='active' ")
    orders=cursor.fetchall()
    cursor.close()
    return jsonify(orders)



@app.route('/admin/confirm_payment/<int:order_id>', methods=['POST'])
def confirm_payment(order_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute("SELECT table_no FROM orders WHERE order_id=%s", (order_id,))
        order = cursor.fetchone()
        if not order:
            return jsonify({'error': 'Invalid order ID'}), 404

        table_no = order['table_no']

       
        cursor.execute("UPDATE orders SET status='completed' WHERE order_id=%s", (order_id,))
        cursor.execute("UPDATE tables SET status='free' WHERE table_no=%s", (table_no,))
        mysql.connection.commit()
        return jsonify({'message': f'Table {table_no} is now free'}), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
