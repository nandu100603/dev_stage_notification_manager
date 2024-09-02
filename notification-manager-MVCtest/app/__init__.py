from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from firebase_admin import credentials, initialize_app
import os
import configparser


# Load configuration
config = configparser.ConfigParser()
config.read("notifier.cfg")
 
db_host = config["DATABASE"]["host"]
db_port = config["DATABASE"]["port"]
db_user = config["DATABASE"]["user"]
db_pass = config["DATABASE"]["password"]
db_name = config["DATABASE"]["database"]
 
app = Flask(__name__)
connectStr = f"mysql+pymysql://{db_user}:{db_pass}@{db_host}/{db_name}"
app.config["SQLALCHEMY_DATABASE_URI"] = connectStr
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
 
db = SQLAlchemy(app)
migrate = Migrate(app, db)
 
cred = credentials.Certificate("C:\\Users\\nandi\\OneDrive\\Desktop\\notification-manager-MVCtest\\bluboy-test-firebase-adminsdk-6k08o-9184a30f9b.json")
initialize_app(cred)
 
from app import routes