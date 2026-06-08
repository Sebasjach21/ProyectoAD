# -*- coding: utf-8 -*-
from psycopg2 import pool
import os

# Cadena de conexión a Supabase – prioriza variable de entorno (Render)
DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres.aifsfrslffnzfufodqwx:47OLPjn1vxbkbL6k@aws-1-us-west-2.pooler.supabase.com:5432/postgres"
)

if not DB_URL:
    raise ValueError("Falta la variable de entorno DATABASE_URL")

DB_POOL = pool.SimpleConnectionPool(1, 20, DB_URL)


def get_connection():
    """Obtener una conexión del pool."""
    try:
        return DB_POOL.getconn()
    except pool.PoolError as exc:
        raise RuntimeError("Pool de conexiones agotado.") from exc


def return_connection(conn):
    """Devolver la conexión al pool."""
    if conn:
        DB_POOL.putconn(conn)
