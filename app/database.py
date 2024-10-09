# app/database.py
import psycopg2
import os

def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv('DATABASE_HOST'),
        database=os.getenv('DATABASE'),
        user=os.getenv('USERMAME'),
        password=os.getenv('PASSWORD')
    )
    return conn