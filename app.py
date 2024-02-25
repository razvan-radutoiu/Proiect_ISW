from datetime import timedelta
import db
import json
from flask import Flask, request, render_template, jsonify, redirect, url_for, session

app = Flask(__name__)
app.secret_key = '1234'

@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template("signin.html")

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    return render_template("signup.html")

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
        session['username'] = username

        if remember_me:
            app.permanent_session_lifetime = timedelta(days=7)
            session.permanent = True
    else:
        session.pop('logged_in', None)
        session.pop('username', None)

    return json.dumps(data)

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect(url_for('home'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    status = db.insert_user()
    return json.dumps(status)

@app.route('/menu', methods=['GET', 'POST'])
def menu():
    menu_data = db.get_menu()
    if not session.get('logged_in'):
        return redirect(url_for('home'))
    else:
        return render_template('menu.html', menu_data=menu_data)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(debug=True)
