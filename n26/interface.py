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
            dbname = self.config["dbname"],
        )
        return conn

    @property
    def close_connection(self):
        self.db_use_session.close()
        
    
    def create_staging_table(self):
        cursor = self.db_use_session.cursor()
        print(cursor)
        cursor.execute('''
        DROP TABLE IF EXISTS TRANSACTIONS;
        CREATE TABLE TRANSACTIONS(
            ID CHAR(100) PRIMARY KEY NOT NULL,
            USER_ID CHAR(100) NOT NULL,
            EXPENSE_TYPE CHAR(10) NOT NULL,
            ACCOUNT_ID CHAR(100) NOT NULL,
            VISIBLE_TS INT8 NOT NULL,
            CREATED_TS INT8 NOT NULL,
            TYPE CHAR(100) NOT NULL,
            TRANSACTION_CODE CHAR(100) NOT NULL,
            TRANSACTION_CODE_DESCRIPTION CHAR(100) NOT NULL,
            AMOUNT FLOAT8 NOT NULL,
            ORIGINAL_AMOUNT FLOAT8 NULL,
            EXCHANGE_RATE CHAR(100) NULL,
            CURRENCY_CODE CHAR(100) NOT NULL,
            MCC INT8 NULL,
            MERCHANT_CITY CHAR(100) NULL,
            MERCHANT_NAME CHAR(100) NULL,
            MERCHANT_NAME_PREPROCESSED CHAR(100) NULL,
            MERCHANT_COUNTRY_CODE INT NULL,
            CATEGORY_N26 CHAR(100) NOT NULL,
            CATEGORY_N26_PREPROCESSED CHAR(100) NOT NULL,
            PARTNER_NAME CHAR(100) NULL,
            REFERENCE_TEXT TEXT NULL,
            REFERENCE_TEXT_PREPROCESSED TEXT NULL,
            TRANSACTION_DESCRIPTION_MERGED TEXT NULL,
            CATEGORY_MODEL CHAR(100) NOT NULL,
            RECURRING BOOL NULL,
            PENDING BOOL NULL,
            CARD_ID CHAR(100) NULL,
            BIC_DESTINATARY CHAR(100) NULL,
            NAME_DESTINATARY CHAR(100) NULL,
            IBAN_DESTINATARY CHAR(100) NULL
        );
        '''
        )
        self.db_use_session.commit()
        print("table is created")


    def execute_query(self, sql_query):
        cursor = self.db_use_session.cursor()
        cursor.execute(sql_query)
        self.db_use_session.commit()
        print("command executed")
        