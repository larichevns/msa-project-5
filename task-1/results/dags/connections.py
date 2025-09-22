"""
Скрипт для создания подключений в Airflow
Запустите этот скрипт после инициализации Airflow
"""

from airflow import settings
from airflow.models import Connection

def create_connections():
    """Создание подключений к базам данных"""

    new_conn = Connection(
        conn_id='postgres_data',
        conn_type='postgres',
        host='postgres-data',
        schema='datadb',
        login='datauser',
        password='datapass',
        port=5433
    )

    session = settings.Session()
    existing = session.query(Connection).filter_by(conn_id='postgres_data').first()

    if not existing:
        session.add(new_conn)
        session.commit()
        print("Connection 'postgres_data' created successfully")
    else:
        print("Connection 'postgres_data' already exists")

    session.close()

if __name__ == "__main__":
    create_connections()