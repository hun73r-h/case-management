import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="zfea5s86cs",  # Change if your password is different
        database="case_management"
    )
