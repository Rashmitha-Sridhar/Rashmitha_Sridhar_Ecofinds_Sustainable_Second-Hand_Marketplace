import mysql.connector

def get_db_connection():
    conn = mysql.connector.connect(
        host="localhost",
        user="Your username",
        password="Your password",
        database="ecofinds"
    )
    return conn
