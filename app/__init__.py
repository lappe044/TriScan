from flask import Flask
from flask_pymongo import PyMongo
from app.config import *

app = Flask(__name__)
app.config["MONGO_URI"] = mongodb_uri
config.mongo = PyMongo(app)

from app import views