import pymongo
from flask import request
import bcrypt

client = pymongo.MongoClient('mongodb://127.0.0.1:27017/')

db = client['university_cafeteria']  # DB name

users = db['users']
menu_items = db['menu_items']

def hash_pass(password):
    
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password

def insert_data():
    pass

def check_user():
    pass

def insert_menu_item():
    pass

def get_menu():
    pass
