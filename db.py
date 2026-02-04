import psycopg
import os
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row

from dotenv import load_dotenv
load_dotenv()
conn = psycopg.connect(
    dbname=os.getenv("POSTGRES_DB"),
    user=os.getenv("POSTGRES_USER"),
    host=os.getenv("POSTGRES_HOST"),
    port=os.getenv("POSTGRES_PORT"),
)

register_vector(conn)
print("connected!")
