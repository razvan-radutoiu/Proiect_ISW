from datetime import timedelta
import db
import json
from flask import Flask, request, render_template, jsonify, redirect, url_for, session
import bcrypt
from bson import ObjectId

app = Flask(__name__)
app.secret_key = '1234'

# Admin login route
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        admin_data = db.admins.find_one({'name': username})

        if admin_data:
            if bcrypt.checkpw(password.encode('utf-8'), admin_data['password']):
                session['admin_logged_in'] = True
                return redirect(url_for('menu'))

    return render_template('admin.html'), 200


@app.route('/', methods=['GET', 'POST'])
def home():
        return render_template("signin.html"), 200

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    return render_template("signup.html"), 200

@app.route('/signin', methods=['POST'])
def signin():
    status, username = db.check_user()
    remember_me = request.form.get('remember-me')

    data = {
        "username": username,
        "status": status
    }

    if status:
        session['logged_in'] = True
        session['admin_logged_in'] = False # !!!
        session['username'] = username

        if remember_me:
            app.permanent_session_lifetime = timedelta(days=7)
            session.permanent = True
    else:
        session.pop('logged_in', None)
        session.pop('username', None)
        data["error"] = "Invalid credentials"

    return json.dumps(data), 200

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    session.pop('cart', None)

    return redirect(url_for('home'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    status = db.insert_user()
    return json.dumps(status), 200

@app.route('/menu', methods=['GET', 'POST'])
def menu():
    menu_data = db.get_menu()
    num_items_in_cart = sum(session.get('cart', {}).values())

    print(session.get('admin_logged_in')) # note to self: don't forget to pop user session variable
    if session.get('admin_logged_in'):
        if request.method == 'POST':
            action = request.form.get('action')

            if action == 'add':
                db.add_menu_item(request.form['name'], request.form['description'], request.form['price'],
                                 request.form['image_url'])
            elif action == 'remove':
                item_id = request.form.get('item_id')
                db.remove_menu_item(item_id)
                return redirect(url_for('menu'))
            elif action == 'edit':
                item_id = request.form.get('item_id')
                name = request.form.get('name')
                description = request.form.get('description')
                price = request.form.get('price')
                image_url = request.form.get('image_url')
                db.edit_menu_item(item_id, name, description, price, image_url)

            return redirect(url_for('menu'))

        menu_data = db.get_menu()

        return render_template('menu.html', menu_data=menu_data, admin_logged_in = True, num_items_in_cart=num_items_in_cart)

    elif not session.get('logged_in'):
        return redirect(url_for('home'))

    return render_template('menu.html', menu_data=menu_data, admin_logged_in = False, num_items_in_cart=num_items_in_cart)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    item_id = request.form.get('item_id')
    quantity = int(request.form.get('quantity', 1))

    #print(item_id)

    # Validate item_id
    if not item_id:
        return "Item ID is empty", 400

    if 'cart' not in session:
        session['cart'] = {}

    print(session)

    if item_id in session['cart']:
        session['cart'][item_id] += quantity
    else:
        session['cart'][item_id] = quantity
        print(session)
    session.modified = True
    return redirect(url_for('menu'))

@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    item_id = request.form.get('item_id')
    print(f"ITEM ID:{item_id}")
    #print(session['cart'])

    if 'cart' in session and item_id in session['cart']:
        del session['cart'][item_id]
        session.modified = True # !!! Make sure session is saved !!!
    print("UPDATED SESSION CART:")
    #print(session['cart'])

    return redirect(url_for('view_cart'))

@app.route('/cart', methods=['GET'])
def view_cart():
    cart = session.get('cart', {})
    print(session)
    total_price = 0
    #print(session['cart'])

    items_in_cart = []
    for item_id, quantity in cart.items():
        item = db.menu_items.find_one({'_id': ObjectId(item_id)})
        if item:
            item_price = float(item['price'])
            item_total_price = item_price * quantity
            total_price += item_total_price

            items_in_cart.append({
                'item_id': item_id,
                'name': item['name'],
                'description': item['description'],
                'image_url': item['image_url'],
                'price': item_price,
                'quantity': quantity,
                'total_price': item_total_price
            })
        else:

            del session['cart'][item_id]

    print(f"Items in Cart: {items_in_cart}")
    print(f"Total Price: {total_price}")

    return render_template('cart.html', items_in_cart=items_in_cart, total_price=total_price)




@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(debug=True)
