import db
import json
from flask import Flask

app = Flask(__name__)
app.secret_key = '1234'

@app.route('/', methods=['GET', 'POST'])
def home():
    pass

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    pass

@app.route('/signin', methods=['POST'])
def signin():
    pass

@app.route('/logout', methods=['POST'])
def logout():
    pass

@app.route('/register', methods=['GET', 'POST'])
def register():
    pass

@app.route('/menu')
def menu():
    pass

@app.errorhandler(404)
def page_not_found(e):
    pass

if __name__ == '__main__':
    app.run(debug=True)
