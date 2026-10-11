
# MySQL connection test
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from getpass import getpass

password = getpass("Enter your MySQL root password: ")

connection_url = URL.create(
    drivername="mysql+pymysql",
    username="root",
    password=password,
    host="localhost",
    port=3306,
)

engine = create_engine(connection_url)

with engine.connect() as conn:
    print("MySQL version:", conn.execute(text("SELECT VERSION()")).scalar())
    print("MySQL connection successful!")
