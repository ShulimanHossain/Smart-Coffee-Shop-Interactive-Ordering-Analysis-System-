from flask import Flask, render_template,request,redirect,url_for,jsonify,session
from flask_mysqldb import MySQL
import MySQLdb.cursors
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key='my_key_374'
mysql=MySQL (app)

@app.before_request
def check_role():
    # Skip role check for login and home routes
    if request.endpoint in ['login', 'home']:
        return None
    
    protected_routes = {
        'add_item': ['admin'],
        'delete_menu': ['admin'],
        'change_price': ['admin'],
        'updatestock': ['admin'],
        'view_order': ['admin', 'manager'],
        'admin_dashboard': ['admin', 'manager'],
        'confirm_payment': ['admin','manager'],
        'live_orders': ['admin', 'manager'],
        'create_user' : ['admin']
    }

    requested_function = request.endpoint
    if requested_function in protected_routes:
        allowed_roles = protected_routes[requested_function]
        user_role = session.get('role')

        if not user_role:
            return redirect(url_for('login'))
        if user_role not in allowed_roles:
            return "Access Denied! You are not authorized.", 403
    
    return None

@app.route('/')
def home():
    return render_template('login.html')


@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        uid=request.form.get('user_code')
        password=request.form.get('password')

        if not uid or not password:
            return render_template('login.html', message="Please enter both user code and password")

        cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        try:
            cursor.execute("SELECT user_code, password, role FROM User WHERE user_code=%s", (uid,))
            user=cursor.fetchone()
            cursor.close()

            if not user:
                return render_template('login.html', message="User not found")
            
            # Check password
            if password == user['password']:
                session['uid'] = user['user_code']
                session['role'] = user['role']
                return redirect(url_for('admin_dashboard', admin_id=user['user_code']))
            else:
                return render_template('login.html', message="Invalid password")
        except Exception as e:
            cursor.close()
            return render_template('login.html', message=f"Error: {str(e)}")
    else:
        return render_template('login.html')
    

def generate_user_id(role):
    """Generate unique user code like admin01, manager01, etc."""
    cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        # Get the highest number for this role
        cursor.execute("""
            SELECT user_code FROM User 
            WHERE user_code LIKE %s 
            ORDER BY user_code DESC 
            LIMIT 1
        """, (f"{role}%",))
        last_user = cursor.fetchone()
        
        if last_user:
            # Extract the number part (last 2 digits)
            last_code = last_user['user_code']
            # Get the numeric part after the role name
            number_part = last_code[len(role):]
            try:
                next_num = int(number_part) + 1
            except ValueError:
                next_num = 1
        else:
            next_num = 1
        
        return f"{role}{next_num:02d}"
    finally:
        cursor.close()

@app.route('/create_user',methods=['POST'])
def create_user():
     name=request.form.get('name')
     email=request.form.get('email')
     password=request.form.get('password')
     role=request.form.get('role')

     if role not in ['admin', 'manager', 'staff']:
         return jsonify({"error": "Invalid role"}), 400

     user_code=generate_user_id(role)

     cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
     try:
         cursor.execute("INSERT INTO User (user_code, name, email, password, role) VALUES (%s, %s, %s, %s, %s)",
                       (user_code, name, email, password, role))
         mysql.connection.commit()
         user_id=cursor.lastrowid
         return jsonify({"id":user_id,"user_role":role,"user_code":user_code,"msg":"User created"})
     except Exception as e:
         mysql.connection.rollback()
         return jsonify({"error": str(e)}), 500
     finally:
         cursor.close()


@app.route('/admin/<string:admin_id>')
def admin_dashboard(admin_id):
    action = request.args.get('action', 'active')
    cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute("SELECT * FROM Cafe_tables")
        table=cursor.fetchall()
        
        # Get active orders with payment status
        cursor.execute("""
            SELECT o.*, 
                   CASE 
                       WHEN o.payment_status = 'pending' THEN 1 
                       ELSE 0 
                   END as has_payment_request
            FROM Orders o 
            WHERE o.status = 'active' 
            ORDER BY 
                CASE WHEN o.payment_status = 'pending' THEN 0 ELSE 1 END,
                o.order_date DESC, o.order_time DESC
        """)
        active_order = cursor.fetchall()
        
        # Fetch menu if needed for menu-related actions
        menu = []
        if action in ['view_menu', 'delete_menu', 'update_stock', 'change_price']:
            cursor.execute("SELECT * FROM Menu")
            menu = cursor.fetchall()
        
        # Fetch ingredients if needed for Add Item form
        ingredients = []
        if action == 'add':
            cursor.execute("SELECT ing_id, name, quantity, unit FROM Ingredients ORDER BY name")
            ingredients = cursor.fetchall()
        
        cursor.close()
        return render_template('admin_dashboard.html', 
                             admin_id=admin_id, 
                             tables=table, 
                             active_order=active_order,
                             menu=menu,
                             ingredients=ingredients,
                             action=action,
                             manage_item=False)
    except Exception as e:
        cursor.close()
        return f"Error: {str(e)}", 500

@app.route('/admin/<string:admin_id>/change_password', methods=['GET','POST'])
def changepass(admin_id):
     message=''
     
     if request.method=='POST':
             newpass=request.form.get('new_password')
             confirm_pass=request.form.get('confirm_password')
             
             if newpass != confirm_pass:
                 message = "Passwords do not match"
             else:
                 cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                 try:
                     cursor.execute('UPDATE User SET password=%s WHERE user_code=%s',(newpass, admin_id))
                     mysql.connection.commit()
                     message="Successfully changed password"
                 except Exception as e:
                     mysql.connection.rollback()
                     message=f"Error: {str(e)}"
                 finally:
                     cursor.close()
             
     return redirect(url_for('admin_dashboard', admin_id=admin_id, action='change_password', message=message))

@app.route('/admin/<string:admin_id>/menu')
def view_menu(admin_id):
    cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM Menu")
    menu=cursor.fetchall()
    return render_template('admin_dashboard.html',admin_id=admin_id,menu=menu)

@app.route('/admin/<string:admin_id>/add_item', methods=['POST'])
def add_item(admin_id):
    name = request.form.get('name')
    price = float(request.form.get('price'))
    cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    message=''
    
    try:
        # Insert the menu item
        cursor.execute("INSERT INTO Menu (name, price) VALUES (%s, %s)", (name, price))
        mysql.connection.commit()
        item_id = cursor.lastrowid 

        # Handle ingredients - can be existing ingredient IDs or new ingredient data
        ingredient_ids = request.form.getlist('ingredient_id[]')
        ingredient_quantities = request.form.getlist('ingredient_quantity[]')
        new_ingredient_names = request.form.getlist('new_ingredient_name[]')
        new_ingredient_quantities = request.form.getlist('new_ingredient_quantity[]')
        new_ingredient_units = request.form.getlist('new_ingredient_unit[]')

        # Process existing ingredients (selected from dropdown)
        for ing_id, qty in zip(ingredient_ids, ingredient_quantities):
            if ing_id and qty:  # Skip empty values
                cursor.execute("INSERT INTO Item_ingredients (item_id, ing_id, quantity_needed) VALUES (%s, %s, %s)", 
                             (item_id, int(ing_id), float(qty)))
                mysql.connection.commit()

        # Process new ingredients (added via "Add New Ingredient")
        for ing_name, qty, unit in zip(new_ingredient_names, new_ingredient_quantities, new_ingredient_units):
            if ing_name and qty and unit:  # Skip empty values
                # Check if ingredient already exists
                cursor.execute("SELECT ing_id FROM Ingredients WHERE name = %s", (ing_name,))
                result = cursor.fetchone()
                
                if result:
                    ing_id = result['ing_id']
                else:
                    # Insert new ingredient
                    cursor.execute("INSERT INTO Ingredients (name, quantity, unit) VALUES (%s, %s, %s)", 
                                 (ing_name, 0, unit))
                    mysql.connection.commit()
                    ing_id = cursor.lastrowid
                
                # Link ingredient to item
                cursor.execute("INSERT INTO Item_ingredients (item_id, ing_id, quantity_needed) VALUES (%s, %s, %s)", 
                             (item_id, ing_id, float(qty)))
                mysql.connection.commit()

        message = "Item added successfully"
        cursor.close()
        return redirect(url_for('admin_dashboard', admin_id=admin_id, action='add', message=message))
    except Exception as e:
        mysql.connection.rollback()
        message = f"Error adding item: {str(e)}"
        cursor.close()
        return redirect(url_for('admin_dashboard', admin_id=admin_id, action='add', message=message))


@app.route('/admin/<string:admin_id>/item/<int:item_id>', methods=['GET', 'POST'])
def manage_item(admin_id, item_id):
    action = request.args.get('action', 'view')
    message = request.args.get('message', '')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        # Get item details
        cursor.execute("SELECT * FROM Menu WHERE item_id=%s", (item_id,))
        item = cursor.fetchone()
        
        if not item:
            return "Item not found", 404
        
        if request.method == 'POST':
            if action == 'delete_menu':
                try:
                    cursor.execute('DELETE FROM Menu WHERE item_id=%s', (item_id,))
                    mysql.connection.commit()
                    message = "Item deleted successfully"
                    cursor.close()
                    return redirect(url_for('admin_dashboard', admin_id=admin_id, action='delete_menu', message=message))
                except Exception as e:
                    mysql.connection.rollback()
                    message = f"Error deleting item: {str(e)}"
            
            elif action == 'change_price':
                newprice = request.form.get('newprice')
                try:
                    cursor.execute('UPDATE Menu SET price=%s WHERE item_id=%s', (newprice, item_id))
                    mysql.connection.commit()
                    message = "Price changed successfully"
                    cursor.close()
                    return redirect(url_for('admin_dashboard', admin_id=admin_id, action='change_price', message=message))
                except Exception as e:
                    mysql.connection.rollback()
                    message = f"Error changing price: {str(e)}"
            
            elif action == 'update_stock':
                # Get ingredients for this item
                cursor.execute("""
                    SELECT i.ing_id, i.name, i.quantity, i.unit, ii.quantity_needed
                    FROM Ingredients i
                    JOIN Item_ingredients ii ON i.ing_id = ii.ing_id
                    WHERE ii.item_id = %s
                """, (item_id,))
                ingredients = cursor.fetchall()
                
                # Update each ingredient quantity
                for ing in ingredients:
                    ing_id = ing['ing_id']
                    new_quantity = request.form.get(f'quantity_{ing_id}')
                    if new_quantity:
                        try:
                            cursor.execute("UPDATE Ingredients SET quantity=%s WHERE ing_id=%s", (new_quantity, ing_id))
                        except Exception as e:
                            mysql.connection.rollback()
                            message = f"Error updating stock: {str(e)}"
                            cursor.close()
                            return redirect(url_for('manage_item', admin_id=admin_id, item_id=item_id, action='update_stock', message=message))
                
                mysql.connection.commit()
                message = "Stock updated successfully"
                cursor.close()
                return redirect(url_for('admin_dashboard', admin_id=admin_id, action='update_stock', message=message))
        
        # GET request - show form
        if action == 'update_stock':
            # Get ingredients for this item
            cursor.execute("""
                SELECT i.ing_id, i.name, i.quantity, i.unit, ii.quantity_needed
                FROM Ingredients i
                JOIN Item_ingredients ii ON i.ing_id = ii.ing_id
                WHERE ii.item_id = %s
            """, (item_id,))
            ingredients = cursor.fetchall()
        else:
            ingredients = []
        
        cursor.close()
        return render_template('admin_dashboard.html',
                             admin_id=admin_id,
                             item=item,
                             ingredients=ingredients,
                             action=action,
                             message=message,
                             manage_item=True)
    except Exception as e:
        cursor.close()
        return f"Error: {str(e)}", 500

@app.route('/admin/menu/delete_menu',methods=['POST','GET'])
def delete_menu():
    message=''
    cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if request.method=='POST':
        item_id=request.form['item_id']
        try:
            cursor.execute('DELETE FROM Menu WHERE item_id=%s',(item_id,))
            mysql.connection.commit()
            message="Item deleted successfully"
        except Exception as e:
            mysql.connection.rollback()
            message="Error deleting item"
    cursor.execute("SELECT item_id,name FROM Menu")
    menu=cursor.fetchall()
    cursor.close()
    return render_template('admin_dashboard.html',action='delete_menu',menu=menu,message=message)

@app.route('/admin/menu/change_price',methods=['POST','GET'])
def change_price():
    message=''
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    if request.method=='POST':
           item_id=request.form['item_id']
           newprice=request.form['newprice']
           try:
            cursor.execute('UPDATE Menu SET price =%s WHERE item_id=%s ',(newprice,item_id))
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
    cursor.execute("""SELECT  o.*, t.status AS table_status FROM Orders o 
                   JOIN Cafe_tables t ON o.table_no = t.table_no  
                   WHERE o.status='active' 
                   ORDER BY o.order_date, o.order_time""")
    orders=cursor.fetchall()
    cursor.close()
    return render_template('admin/view_order.html',orders =orders)

@app.route('/admin/live_orders',methods=['GET'])
def live_orders():
    """API endpoint to get live orders for real-time updates"""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute("""
            SELECT o.*, 
                   CASE 
                       WHEN o.payment_status = 'pending' THEN 1 
                       ELSE 0 
                   END as has_payment_request
            FROM Orders o 
            WHERE o.status = 'active' 
            ORDER BY 
                CASE WHEN o.payment_status = 'pending' THEN 0 ELSE 1 END,
                o.order_date DESC, o.order_time DESC
        """)
        orders = cursor.fetchall()
        # Convert datetime objects to strings for JSON
        for order in orders:
            if 'order_date' in order and order['order_date']:
                order['order_date'] = str(order['order_date'])
            if 'order_time' in order and order['order_time']:
                order['order_time'] = str(order['order_time'])
        return jsonify({"orders": orders})
    finally:
        cursor.close()


@app.route('/admin/confirm_payment/<int:order_id>', methods=['POST'])
def confirm_payment(order_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        # Get order details
        cursor.execute("SELECT table_no, payment_method FROM Orders WHERE order_id=%s", (order_id,))
        order = cursor.fetchone()
        
        if not order:
            return jsonify({"error": "Order not found"}), 404
        
        # Update order status and payment
        cursor.execute("""
            UPDATE Orders 
            SET payment_status='paid', status='completed' 
            WHERE order_id=%s
        """, (order_id,))
        
        # Free the table
        cursor.execute("UPDATE Cafe_tables SET status='Free' WHERE table_no=%s", (order["table_no"],))
        
        mysql.connection.commit()
        return jsonify({"success": True, "message": "Payment confirmed and order completed"})
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
  

@app.route('/logout')
def logout(): 
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001, debug=True)