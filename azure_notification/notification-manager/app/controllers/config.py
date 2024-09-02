import firebase_admin
from firebase_admin import credentials
import configparser
 
# Read configuration from the config file
class Config:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read(r"../../notifier.cfg")

    def getDBConfig(self):
        db_config = {
            'host': self.config["DATABASE"]["host"],
            'user': self.config["DATABASE"]["user"],
            'password': self.config["DATABASE"]["password"],
            'database': self.config["DATABASE"]["database"]
        }

        return db_config
    
    def initializeFirebaseApp(self):
        path_to_firebase_app_sdk=self.config["DEFAULT"]["path_to_firebase_app_sdk"]
        cred = credentials.Certificate(path_to_firebase_app_sdk)
        try:
            firebase_admin.initialize_app(cred)
        except ValueError:
            # Firebase app is already initialized
            pass
