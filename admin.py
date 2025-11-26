from flask import Flask, render_template,request,redirect,url_for,jsonify,session
from flask_mysqldb import MySQL
import MySQLdb.cursors
from config import Config
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key='my_key_374'
mysql=MySQL (app)

@app.before_request
def check_role():
    protected_routes = {
        'add_item': ['admin'],
        'delete_menu': ['admin'],
        'change_price': ['admin'],
        'updatestock': ['admin'],
        'view_order': ['admin', 'manager'],
        'admin_dashboard': ['admin', 'manager'],
        'confirm_payment': ['admin','manager'],
        'generate_user_id' :['admin'],
        'create_user' : ['admin']
    }

    requested_function = request.endpoint
    if requested_function in protected_routes:
        allowed_roles = protected_routes[requested_function]
        user_role = session.get('role')

        if not user_role :
            return redirect(url_for('login'))
        if user_role not in allowed_roles:
            return "Access Denied! You are not authorized.", 403

@app.route('/')
def home():
    return render_template('login.html')


@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        uid=request.form['user_code']
        password=request.form['password']

        cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute("SELECT user_code,password,role FROM User WHERE user_code=%s",(uid,))
        user=cursor.fetchone()

    if not user :
        return render_template('admin/login.html', message="User not found")
    
    if password== uid[password]:
        session['uid']=user['user_code']
        session['role']=user['role']
        return redirect(url_for('admin_dashboard',admin_id=user['user_code']))
    else :
        return render_template('admin/login.html',message="Invalid password")
    

def generate_user_id(role):
    cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT COUNT(*) AS count FROM users WHERE role =%s", (role,))
    data=cursor.fetchone()
    code=data["count"] + 1
    cursor.close()
    return f"{role}{code:02}"

@app.route('/create_user',methods=['POST'])
def create_user():
     name=request.form.get('name')
     email=request.form.get('email')
     password=request.form.get('password')
     role=request.form.get('role')

     user_code=generate_user_id(role)

     cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
     cursor.execute("INSERT INTO users (user_id,name,email,password,role) VALUES (%s,%s,%s,%s,%s)",
                   (user_code, name, email, password, role))
     mysql.connection.commit()
     user_id=cursor.lastrowid
     cursor.close()
     
     return jsonify({"id":user_id,"user_role":role,"user_code":user_code,"msg":"User created"})


@app.route('/admin/<string:admin_id>')
def admin_dashboard(admin_id):
    cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT *  FROM tables")
    table=cursor.fetchall()
    cursor.execute("SELECT * FROM orders WHERE status ='active' ORDER BY timestamp DESC")
    active_order =cursor.fetchall()
    return render_template('admin/admin_dashboard.html',admin_id=admin_id,tables=table,active_order=active_order)

@app.route('/admin/<string:admin_id>')
def changepass():
     message=''
     
     if request.method=='POST':
             uid=request.form['admin_id']
             newpass=request.form['newpassword']
             cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
             cursor.execute('UPDATE Admin SET admin_password=%s WHERE user_code=%s',(newpass,uid))
             mysql.connection.commit()
             message="Successfully changed password"
             
     return render_template('admin/admin_dashboard.html',user_code=uid,message=message)

@app.route('/admin/<int:admin_id>/menu')
def view_menu(admin_id):
    cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM Menu")
    menu=cursor.fetchall()
    return render_template('admin/admin_dashboard.html',admin_id=admin_id,menu=menu)

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
    
    return redirect(url_for('admin/admin_dashboard',action='add_item',message=message, admin_id=admin_id))


@app.route('/admin/menu/delete_menu',methods=['POST','GET'])
def delete_menu():
    message=''
    cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if request.method=='POST':
        item_id=request.form['item_id']
        try:
            cursor.execute('DELETE FROM menu WHERE item_id=%s',(item_id,))
            mysql.connection.commit()
            message="Item deleted successfully"
        except Exception as e:
            mysql.connection.rollback()
            message="Error deleting item"
    cursor.execute("SELECT item_id,name FROM menu")
    menu=cursor.fetchall()
    cursor.close()
    return render_template('admin/delete_menu.html',action='delete_menu',menu=menu,message=message)

@app.route('/admin/menu/change_price',methods=['POST','GET'])
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
    return render_template('admin/change_price.html',action='change_price',menu=menu,message=message)

@app.route('/admin/updatestock', methods=['GET','POST'])
def updatestock():
      message=''
      if request.method=='POST':
           ing_id=request.form['ing_id']
           new_quantity=request.form['new_quantity']
           cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
           try: 
            cursor.execute("UPDATE ingredients SET quantity=%s WHERE  ing_id=%s",(new_quantity,ing_id))
            mysql.connection.commit()
            message="successfully update stock"
           except Exception as e:
            mysql.connection.rollback()
            print("Error deleting:", e)  
      cursor.execute("SELECT ing_id,name, quantity FROM Ingredients")
      ingredients=cursor.fetchall()
      cursor.close()
      return render_template('admin/update_stock.html',action='updatestock',ingredients=ingredients,message=message)

@app.route('/admin/order',methods=['GET'])
def view_order():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""SELECT  o.*, t.status AS table_status FROM orders o 
                   JOIN cafe_tables t ON o.table_no = t.table_no  
                   WHERE o.status='active' 
                   ORDER BY o.order_date, o.order_time""")
    orders=cursor.fetchall()
    cursor.close()
    return render_template('admin/view_order.html',orders =orders)


@app.route('/admin/confirm_payment/<int:order_id>', methods=['POST'])
def confirm_payment(order_id):
    status=request.form.get('status')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if status =="completed":
        cursor.execute("""UPDATE Orders SET payment_status='paid', order_status='completed'
                       WHERE order_id=%s """,(order_id,))
        cursor.execute("""UPDATE cafe_tables SET status='Free' 
                       WHERE table_no=(SELECT table_no FROM Orders WHERE order_id=%s)""",(order_id,))
        mysql.connection.commit()
        cursor.close()
        return "Completed"
    elif status =="failed":
        cursor.close()
        return "Failed"
    elif status =="pending":
        cursor.close()
        return "Pending"
  

@app.route('/logout')
def logout(): 
    session.clear()
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)