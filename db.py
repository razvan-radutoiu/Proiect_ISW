import pymongo
from flask import request, jsonify
import bcrypt
from bson import ObjectId
from datetime import datetime

client = pymongo.MongoClient('mongodb://127.0.0.1:27017/')

db = client['university_cafeteria']  # DB name
users = db['users']
menu_items = db['menu_items']
admins = db['admins']


def hash_pass(password):
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password


def insert_user():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['pass']

        hashed_password = hash_pass(password)

        reg_user = {
            'name': name,
            'email': email,
            'password': hashed_password,
            'role': 'customer',  # user role
            'date_created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'orders': []
        }

        if users.find_one({"email": email}) is None:
            users.insert_one(reg_user)
            return True
        else:
            return False, "User already in database"


def check_user():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['pass']

        user = {
            "email": email
        }

        user_data = users.find_one(user)
        if user_data is None:
            return False, ""
        else:
            if bcrypt.checkpw(password.encode('utf-8'), user_data["password"]):
                return True, user_data["name"]
            else:
                return False, "False"


def add_menu_item(name, description, price, image_url):
    menu_item_id = ObjectId()

    menu_item = {
        "_id": menu_item_id,
        "name": name,
        "description": description,
        "price": price,
        "image_url": image_url
    }

    menu_items.insert_one(menu_item)



def remove_menu_item(item_id):
    item_id = ObjectId(item_id)
    menu_items.delete_one({"_id": item_id})


def get_menu():
    return menu_items.find({})


def edit_menu_item(item_id, name, description, price, image_url):
    item_id = ObjectId(item_id)

    updated_menu_item = {
        "name": name,
        "description": description,
        "price": price,
        "image_url": image_url
    }

    menu_items.update_one({"_id": item_id}, {"$set": updated_menu_item})


def save_order(username, order_data):
    user_data = users.find_one({'name': username})

    if user_data:
        user_id = user_data['_id']
        users.update_one(
            {'name': username},
            {'$push': {'orders': order_data}}
        )
    else:
        print(f"User with username {username} not found in the database.")
