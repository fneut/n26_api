import json
from os.path import dirname, abspath
from typing import Optional
import psycopg2
import os.path
import yaml

class Interface():
    def __init__(self,environment: Optional[str] = None,config=None):
        self.environment = "dev",
        self.path = dirname(dirname(abspath(__file__)))
        # self.path = os.path.dirname(__file__)
        if config is None:
            with open(f"{self.path}/credentials_db.yaml", "r") as stream:
                try:
                    self.config = yaml.safe_load(stream)["dev"]
                except yaml.YAMLError as exc:
                    print(exc)
        self.db_use_session = self.postgresql_connect()
    
    def postgresql_connect(self):
        conn = psycopg2.connect(
            host = self.config["host"],
            user = self.config["user"],
            password = self.config["password"],
            port = self.config["port"],
        )
        return conn

    @property
    def close_connection(self):
        self.db_use_session.close()
        
    

