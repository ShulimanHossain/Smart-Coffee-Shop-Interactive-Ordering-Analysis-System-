from flask import Flask, render_template,request,redirect,url_for,jsonify,session
from flask_mysqldb import MySQL
import MySQLdb.cursors
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key='my_key_374'
mysql=MySQL (app)

@app.route('/',methods=['GET','POST'])
def home():
    cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
               cursor.execute("""SELECT table_no, status FROM Cafe_tables""")
               table=cursor.fetchall()

               cursor.execute("""SELECT  item_id, name, price FROM Menu""")
               menu=cursor.fetchall()
               
    finally:
               cursor.close()
    return render_template("home.html",table=table,menu=menu)

@app.route('/check_stock',methods=['POST'])
def check_stock():
         data=request.get_json()
         item_id=data.get("item_id")
         quantity=data.get("quantity",1)
         cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
         cursor.execute("""SELECT  Ingredients.quantity, Item_ingredients.quantity_needed
                        FROM Item_ingredients 
                        JOIN Ingredients ON Item_ingredients.ing_id=Ingredients.ing_id
                        WHERE Item_ingredients.item_id=%s""",(item_id,))
         ingredient=cursor.fetchall()
         for ing in ingredient :
                 if ing["quantity"] < ing["quantity_needed"] * quantity:
                         return "Not enough ingredients"
         return jsonify({"available": True})

@app.route('/order/create',methods=['POST'])
def create_order():
         data=request.get_json()
         cart=data["cart"] 
         table_no=data["table_no"]
         
         cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
         
         total_price=0.0
         for item in cart:
           item_id=item["item_id"]
                 
           cursor.execute("""SELECT  Ingredients.quantity, Item_ingredients.quantity_needed
                            FROM Item_ingredients 
                          JOIN Ingredients ON Item_ingredients.ing_id=Ingredients.ing_id
                          WHERE Item_ingredients.item_id=%s""",(item_id,))
           ingredient=cursor.fetchall()
           for ing in ingredient :
                   available = ing["quantity"]
                   required = ing["quantity_needed"]
                   if available < required * item["quantity"]:
                           return "Not enough ingredients"
                   
           total_price+=item["price"]* item["quantity"]

         cursor.execute("""
           INSERT INTO Orders (table_no, total_bill, status)
          VALUES (%s, %s, 'active')
           """, (table_no, total_price))
         order_id = cursor.lastrowid
         update_stock_order_save(cursor,cart,order_id)
         return jsonify({"order_id": order_id})

@app.route('/order/<int:order_id>')
def get_order(order_id):
      cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
      try: 
             cursor.execute("SELECT * FROM Orders WHERE order_id = %s", (order_id,))
             order = cursor.fetchone()
             if not order:
                  return "Order not found", 404
             
             cursor.execute("""
                        SELECT OD.item_id, M.name, OD.quantity, M.price
                     FROM Order_details OD
                     JOIN Menu M ON M.item_id = OD.item_id
                     WHERE OD.order_id = %s
                        """, (order_id,))
             items = cursor.fetchall()
      finally:
             cursor.close()
      return jsonify({"order": order, "items": items})


@app.route("/order/<int:order_id>/add_items", methods=["POST"])
def add_more_items(order_id):
           data = request.get_json()
           cart = data["cart"]
           cursor=mysql.connection.cursor(MySQLdb.cursors.DictCursor)
           try :
                cursor.execute("SELECT status FROM Orders WHERE order_id=%s", (order_id,))
                order = cursor.fetchone()
                if not order or order["status"] != "active":
                  return jsonify({"error": "Order closed or not found"}), 400
                total_price=0.0
                for item in cart:
                       item_id=item["item_id"]
                       cursor.execute("""SELECT  Ingredients.quantity, Item_ingredients.quantity_needed
                            FROM Item_ingredients 
                          JOIN Ingredients ON Item_ingredients.ing_id=Ingredients.ing_id
                          WHERE Item_ingredients.item_id=%s""",(item_id,))
                       ingredient=cursor.fetchall()
                       for ing in ingredient :
                         available = ing["quantity"]
                         required = ing["quantity_needed"]
                         if available < required * item["quantity"]:
                            return "Not enough ingredients"
                   
                       total_price+=item["price"]* item["quantity"]
                update_stock_order_save(cursor, cart, order_id)
                cursor.execute("UPDATE Orders SET total_bill = total_bill + %s WHERE order_id = %s", (total_price, order_id))
                
           finally:
                  cursor.close()
           return jsonify({"message": "Items added successfully"})

def update_stock_order_save(cursor, cart, order_id):
    for item in cart:
        cursor.execute("""
            INSERT INTO Order_details (order_id,item_id, quantity)
            VALUES (%s, %s, %s)
        """, (order_id, item["item_id"], item["quantity"]))

        cursor.execute("""
            SELECT ing_id, quantity_needed
            FROM Item_ingredients
            WHERE item_id=%s
        """, (item["item_id"],))

        for ing in cursor.fetchall():
            cursor.execute("""
                UPDATE Ingredients
                SET quantity = quantity - %s
                WHERE ing_id=%s
            """, (ing["quantity_needed"] * item["quantity"], ing["ing_id"]))
@app.route("/order/<int:order_id>/finalize", methods=["POST"])
def finalize_order(order_id):

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("UPDATE Orders SET status='completed' WHERE order_id=%s", (order_id,))

    return jsonify({"message": "Order finalized"})
@app.route("/order/<int:order_id>/summary")
def order_summary(order_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("SELECT * FROM Orders WHERE order_id=%s", (order_id,))
    order = cursor.fetchone()

    cursor.execute("""
        SELECT M.name, OD.quantity, M.price
        FROM Order_details OD
        JOIN Menu M ON M.item_id = OD.item_id
        WHERE OD.order_id = %s
    """, (order_id,))
    items = cursor.fetchall()

    cursor.close()

    return render_template("order_summary.html", order=order, items=items)


if __name__ =="__main__":
    app.run(debug=True)