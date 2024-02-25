from datetime import timedelta
import db
import json
from flask import Flask, request, render_template, jsonify, redirect, url_for, session
import bcrypt

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
    return redirect(url_for('home'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    status = db.insert_user()
    return json.dumps(status), 200

@app.route('/menu', methods=['GET', 'POST'])
def menu():
    menu_data = db.get_menu()

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

        menu_data = db.get_menu()

        return render_template('menu.html', menu_data=menu_data, admin_logged_in = True)

    elif not session.get('logged_in'):
        return redirect(url_for('home'))

    return render_template('menu.html', menu_data=menu_data, admin_logged_in = False)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(debug=True)
