import uuid
from datetime import timedelta, datetime

import db
import json
from flask import Flask, request, render_template, jsonify, redirect, url_for, session, Response
import bcrypt
from bson import ObjectId
from functools import wraps

app = Flask(__name__)
app.maintenance_mode = False  # New variable to track maintenance mode status
app.secret_key = '1234'


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' and 'admin_logged_in' not in session:
            return redirect(url_for('home'))  # Redirect to the login page
        return f(*args, **kwargs)

    return decorated_function


def check_maintenance_mode():
    if 'admin_logged_in' in session:
        return None
    elif app.maintenance_mode:
        return render_template('maintenance_mode.html')
    else:
        return None


# ROUTES
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    session.pop('logged_in', None)
    session.pop('username', None)
    session.pop('cart', None)
    session.pop('admin_logged_in', None)
    session.pop('staff_logged_in', None)


    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        admin_data = db.admins.find_one({'name': username})
        staff_name = admin_data['name']
        print(admin_data)

        if admin_data and 'role' in admin_data:
            role = admin_data['role']
            if role == 'admin' and bcrypt.checkpw(password.encode('utf-8'), admin_data['password']):
                session['admin_logged_in'] = True
                return redirect(url_for('menu'))
            elif role == 'staff' and bcrypt.checkpw(password.encode('utf-8'), admin_data['password']):
                session['staff_logged_in'] = True
                session['username'] = staff_name
                return redirect(url_for('menu'))

    return render_template('admin.html'), 200


@app.route('/', methods=['GET', 'POST'])
def home():
    maintenance_mode_response = check_maintenance_mode()
    if maintenance_mode_response and 'admin_logged_in' not in session:
        return maintenance_mode_response

    if 'logged_in' and 'admin_logged_in' in session:
        return redirect(url_for('menu'))
    return render_template("signin.html"), 200


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'logged_in' and 'admin_logged_in' in session:
        return redirect(url_for('menu'))

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
        session['admin_logged_in'] = False  # !!!
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
    session.pop('admin_logged_in', None)
    session.pop('staff_logged_in', None)

    return redirect(url_for('home'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    status = db.insert_user()
    return json.dumps(status), 200


@app.route('/menu', methods=['GET', 'POST'])
def menu():
    maintenance_mode_response = check_maintenance_mode()
    if maintenance_mode_response and 'admin_logged_in' not in session:
        return maintenance_mode_response

    menu_data = db.get_menu()
    num_items_in_cart = sum(session.get('cart', {}).values())

    print(session)

    if session.get('admin_logged_in') or session.get('staff_logged_in'):
        '''In Flask-PyMongo, find() returns a cursor, not the actual documents.'''
        users_cursor = db.users.find({'role': 'customer'})
        users = list(users_cursor)

        menu_items_cursor = db.menu_items.find()
        menu_items = list(menu_items_cursor)

        print(menu_items)



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
            elif action == 'toggle_maintenance':
                app.maintenance_mode = not app.maintenance_mode

            return redirect(url_for('menu'))

        menu_data = db.get_menu()

        # Convert item IDs in orders to ObjectId
        for user in users:
            for order in user['orders']:
                for item in order['items']:
                    item['item_id'] = ObjectId(item['item_id'])

        return render_template('menu.html', menu_data=menu_data, admin_logged_in=session.get('admin_logged_in', False),
                               staff_logged_in=session.get('staff_logged_in', False),
                               num_items_in_cart=num_items_in_cart, maintenance_mode=app.maintenance_mode, users=users, menu_items=menu_items)

    elif not session.get('logged_in'):
        return redirect(url_for('home'))

    return render_template('menu.html', menu_data=menu_data, admin_logged_in=False, staff_logged_in=False,
                           num_items_in_cart=num_items_in_cart)



@app.route('/add_to_cart', methods=['POST', 'GET'])
@login_required
def add_to_cart():
    maintenance_mode_response = check_maintenance_mode()
    if maintenance_mode_response:
        return maintenance_mode_response

    item_id = request.form.get('item_id')
    quantity = int(request.form.get('quantity', 1))

    # Validate item_id
    if not item_id:
        return "Item ID is empty", 400

    if 'cart' not in session:
        session['cart'] = {}

    print(session)

    if item_id in session['cart']:
        session['cart'][item_id] += quantity
    else:
        session['cart'][item_id] = quantity # <-- sends back a cookie/session update
        print(session)
    session.modified = True
    return redirect(url_for('menu'))


@app.route('/remove_from_cart', methods=['POST', 'GET'])
@login_required
def remove_from_cart():
    item_id = request.form.get('item_id')
    print(f"ITEM ID:{item_id}")

    if 'cart' in session and item_id in session['cart']:
        del session['cart'][item_id]
        session.modified = True  # !!! Make sure session is saved !!!
    print("UPDATED SESSION CART:")

    return redirect(url_for('view_cart'))


@app.route('/cart', methods=['GET'])
@login_required
def view_cart():
    maintenance_mode_response = check_maintenance_mode()
    if maintenance_mode_response:
        return maintenance_mode_response

    cart = session.get('cart', {})
    print(session)
    total_price = 0
    # print(session['cart'])

    items_in_cart = []
    for item_id, quantity in cart.items():
        item = db.menu_items.find_one({'_id': ObjectId(item_id)})
        if item:
            item_price = float(item['price'])
            item_total_price = item_price * quantity
            total_price += item_total_price

            global total
            total = total_price

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


import base64
import qrcode
from qrcode.image.styledpil import StyledPilImage
from io import BytesIO

daily_order_counts = {}


@app.route('/cart/checkout', methods=['POST'])
@login_required
def checkout():
    maintenance_mode_response = check_maintenance_mode()
    if maintenance_mode_response:
        return maintenance_mode_response

    items_in_cart = session.get('cart', [])
    customer = session.get('username')
    print(customer)
    session['transaction_made'] = False
    total_price = total

    if not items_in_cart:
        return redirect(url_for('menu'))

    if session.get('transaction_made'):
        # If a transaction has already been made, redirect to the menu
        return redirect(url_for('menu'))

    today = datetime.now().date().isoformat()

    daily_order_counts.setdefault(today, 0)
    daily_order_counts[today] += 1

    transaction_id = str(uuid.uuid4())

    order_number = f"{today.replace('-', '')}-{daily_order_counts[today]:04d}"

    order_items = []
    for item_id, quantity in items_in_cart.items():
        order_items.append({
            'item_id': item_id,
            'quantity': quantity
        })

    order_data = {
        'order_id': transaction_id,
        'order_date': datetime.now().isoformat(),
        'total_price': total_price,
        'items': order_items
    }

    # db.save_order(session['username'], order_data)

    qr_data = {
        'customer': customer,
        'transaction_id': transaction_id,
        'items_in_cart': items_in_cart,
        'total_price': total_price
    }
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,

    )
    qr.add_data(str(qr_data))
    qr.make(fit=True)

    qr_img = qr.make_image(image_factory=StyledPilImage, embeded_image_path="static/images/logo.png")

    qr_image_io = BytesIO()
    qr_img.save(qr_image_io, format='PNG', compress_level=0)
    qr_image_base64 = base64.b64encode(qr_image_io.getvalue()).decode()

    order_data['qr_image_base64'] = qr_image_base64
    db.save_order(session['username'], order_data)

    session.pop('cart')
    session['transaction_made'] = True

    return render_template('checkout.html', transaction_id=transaction_id, qr_image_base64=qr_image_base64,
                           order_number=order_number)


@app.route('/orders', methods=['GET'])
@login_required
def view_orders():
    maintenance_mode_response = check_maintenance_mode()
    if maintenance_mode_response:
        return maintenance_mode_response

    username = session.get('username')
    user_data = db.users.find_one({'name': username})

    if not user_data:
        return "User not found", 404

    orders = user_data.get('orders', [])

    formatted_orders = []
    for order in orders:
        order_date = datetime.fromisoformat(order['order_date'])
        order_items = []
        items = order.get('items', [])
        for item in items:
            menu_item = db.menu_items.find_one({'_id': ObjectId(item['item_id'])})
            if menu_item:
                order_items.append({
                    'name': menu_item['name'],
                    'quantity': item['quantity']
                })

        qr_image_base64 = order.get('qr_image_base64', '')

        formatted_order = {
            'id': order['order_id'],
            'order_date': order_date.strftime('%Y-%m-%d %H:%M:%S'),
            'total_price': order['total_price'],
            'items': order_items,
            'qr_image_base64': qr_image_base64
        }

        formatted_orders.append(formatted_order)

    return render_template('orders.html', orders=formatted_orders)

from flask import make_response

@app.route('/orders/<order_id>/delete', methods=['POST'])
#@login_required
def delete_order(order_id):
    username = session.get('username')
    order = db.users.find_one({'orders.order_id': order_id, 'name': username})

    customer = request.cookies.get('customer')
    print(customer)
    if customer:
        order = db.users.find_one({'orders.order_id': order_id, 'name': customer})
        db.users.update_one(
            {'name': customer},
            {'$pull': {'orders': {'order_id': order_id}}}
        )



    if not order:
        return "Order not found or user is not authorized to delete it.", 400

    db.users.update_one(
        {'name': username},
        {'$pull': {'orders': {'order_id': order_id}}}
    )
    response_text = "Order deleted successfully."
    response = make_response(response_text, 302)
    response.headers['Location'] = url_for('view_orders')
    return response


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port='5000', debug=True)
