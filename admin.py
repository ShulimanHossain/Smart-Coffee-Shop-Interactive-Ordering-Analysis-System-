from flask import Flask, render_template,request,redirect,url_for,jsonify,session
from flask_mysqldb import MySQL
import MySQLdb.cursors
from config import Config

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
