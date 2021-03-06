from flask import Flask
import petl as etl
from sqlalchemy import create_engine
import sys
import pymysql
import pymongo
import pprint

def get_full_name(record):
    return record['first_name'] + ' ' + record['last_name']

def get_company_name(record):
    parts = record['email'].split('@')
    if len(parts) >= 1:
        return parts[1]
    else:
        return ''

class CursorProxy(object):
     def __init__(self, cursor):
         self._cursor = cursor
     def executemany(self, statement, parameters, **kwargs):
         # convert parameters to a list
         parameters = list(parameters)
         # pass through to proxied cursor
         return self._cursor.executemany(statement, parameters, **kwargs)
     def __getattr__(self, item):
         return getattr(self._cursor, item)

def get_cursor(connection):
     return CursorProxy(connection.cursor())

print('starting etl server', file=sys.stdout)

def mongo_etl():
    try:
        print("loading csv data")
        data = etl.fromcsv('DATA.csv')
        print("tranforming data")
        data = etl.addfield(data, 'full_name', lambda record: get_full_name(record))
        data = etl.addfield(data, 'company', lambda record: get_company_name(record))
        print("loading data to mongo")
        # print(data)
        uri = "mongodb://root:root@localhost/?authenticationDatabase=admin"
        client = pymongo.MongoClient(uri)
        db = client['sfl']
        users = db['users']
        users.drop()
        # cursor = users.find({})
        # for document in cursor:
        #   print(document)
        i = 0 
        for rec in data:
            if i == 0:
                headers = rec
            else:
                mongo_doc = {}
                for header, column in zip(headers, rec):
                    mongo_doc[header] = column      

                users.insert_one(mongo_doc)
            i = i + 1
        return 'Mongo ETL Completed'
    except Exception as error:
        print("etl for mysql has error")
        print('error message: {}'.format(error))
        return str(error)


def mysql_etl():
    try:
        print("extracting csv data", file=sys.stdout)
        data = etl.fromcsv('DATA.csv')
        print("tranforming data", file=sys.stdout)
        data = etl.addfield(data, 'full_name', lambda record: get_full_name(record))
        data = etl.addfield(data, 'company', lambda record: get_company_name(record))
        print("loading data to mysql", file=sys.stdout)
        engine = create_engine('mysql+pymysql://root:root@172.31.14.230/sfl')
        connection = engine.raw_connection()
        connection.cursor().execute('SET SQL_MODE=ANSI_QUOTES')
        connection.cursor().execute('DROP TABLE IF EXISTS users;')
        etl.todb(data, get_cursor(connection) , 'users', create=True)
        return 'MySQL ETL Completed'
    except Exception as error:
        print("etl for mysql has error", file=sys.stdout)
        print('error message: {}'.format(error), file=sys.stdout)
        return str(error)

