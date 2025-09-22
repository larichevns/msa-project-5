from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.operators.bash_operator import BashOperator
from airflow.operators.email_operator import EmailOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python import BranchPythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.models import Variable
from airflow.utils.trigger_rule import TriggerRule
import pandas as pd
import os
import logging

# Конфигурация DAG
default_args = {
    'owner': 'data_team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email': ['larichevns@gmail.com'],
    'email_on_failure': True,
    'email_on_retry': True,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'retry_exponential_backoff': True,
    'max_retry_delay': timedelta(minutes=30),
}

dag = DAG(
    'data_processing_pipeline',
    default_args=default_args,
    description='Пайплайн для обработки данных из различных источников',
    schedule_interval='@daily',
    catchup=False,
    tags=['production', 'data_processing'],
)

def read_postgres_data(**context):
    """
    Чтение данных из PostgreSQL
    """
    logging.info("Начинаем чтение данных из PostgreSQL")

    try:
        # Подключение к базе данных
        pg_hook = PostgresHook(postgres_conn_id='postgres_data')

        # Запрос данных о заказах
        orders_query = """
        SELECT
            o.order_id,
            o.customer_id,
            o.order_date,
            o.total_amount,
            o.status as order_status,
            c.name as customer_name,
            c.email,
            c.city,
            p.payment_method,
            p.status as payment_status
        FROM orders o
        LEFT JOIN customers c ON o.customer_id = c.customer_id
        LEFT JOIN payments p ON o.order_id = p.order_id
        WHERE o.order_date >= CURRENT_DATE - INTERVAL '7 days'
        """

        orders_df = pd.DataFrame(
            pg_hook.get_records(orders_query),
            columns=['order_id', 'customer_id', 'order_date', 'total_amount',
                    'order_status', 'customer_name', 'email', 'city',
                    'payment_method', 'payment_status']
        )

        logging.info(f"Загружено {len(orders_df)} записей из базы данных")

        # Сохранение данных для последующей обработки
        orders_df.to_csv('/opt/airflow/data/postgres_orders.csv', index=False)

        # Передача метрик в XCom
        context['task_instance'].xcom_push(key='postgres_records_count', value=len(orders_df))
        context['task_instance'].xcom_push(key='total_amount', value=float(orders_df['total_amount'].sum()))

        return f"Успешно загружено {len(orders_df)} записей"

    except Exception as e:
        logging.error(f"Ошибка при чтении из PostgreSQL: {str(e)}")
        raise

def read_csv_data(**context):
    """
    Чтение данных из CSV файлов
    """
    logging.info("Начинаем чтение CSV файлов")

    try:
        csv_path = '/opt/airflow/data/delivery_status.csv'

        if os.path.exists(csv_path):
            delivery_df = pd.read_csv(csv_path)
            logging.info(f"Загружено {len(delivery_df)} записей из CSV")

            # Анализ данных о доставках
            delivery_stats = {
                'total_deliveries': len(delivery_df),
                'delivered': len(delivery_df[delivery_df['delivery_status'] == 'delivered']),
                'in_transit': len(delivery_df[delivery_df['delivery_status'] == 'in_transit']),
                'preparing': len(delivery_df[delivery_df['delivery_status'] == 'preparing'])
            }

            # Сохранение обработанных данных
            delivery_df.to_csv('/opt/airflow/data/processed_deliveries.csv', index=False)

            # Передача метрик в XCom
            context['task_instance'].xcom_push(key='csv_records_count', value=len(delivery_df))
            context['task_instance'].xcom_push(key='delivery_stats', value=delivery_stats)

            return f"CSV обработан: {delivery_stats}"
        else:
            logging.warning("CSV файл не найден")
            context['task_instance'].xcom_push(key='csv_records_count', value=0)
            return "CSV файл не найден"

    except Exception as e:
        logging.error(f"Ошибка при чтении CSV: {str(e)}")
        raise

def analyze_data_quality(**context):
    """
    Анализ качества данных и определение ветвления
    """
    logging.info("Анализируем качество данных")

    # Получение метрик из предыдущих задач
    postgres_count = context['task_instance'].xcom_pull(key='postgres_records_count')
    csv_count = context['task_instance'].xcom_pull(key='csv_records_count')
    total_amount = context['task_instance'].xcom_pull(key='total_amount')

    logging.info(f"PostgreSQL записей: {postgres_count}")
    logging.info(f"CSV записей: {csv_count}")
    logging.info(f"Общая сумма заказов: {total_amount}")

    # Логика ветвления на основе анализа данных
    quality_issues = []

    if postgres_count == 0:
        quality_issues.append("Нет данных из PostgreSQL")

    if csv_count == 0:
        quality_issues.append("Нет данных из CSV")

    if total_amount and total_amount < 10000:
        quality_issues.append(f"Низкая сумма заказов: {total_amount}")

    # Определение следующего шага на основе качества данных
    if len(quality_issues) > 0:
        logging.warning(f"Обнаружены проблемы с качеством данных: {quality_issues}")
        context['task_instance'].xcom_push(key='quality_issues', value=quality_issues)
        return 'handle_data_quality_issues'
    else:
        logging.info("Качество данных в норме")
        return 'process_normal_flow'

def handle_quality_issues(**context):
    """
    Обработка проблем с качеством данных
    """
    issues = context['task_instance'].xcom_pull(key='quality_issues')
    logging.warning(f"Обработка проблем качества данных: {issues}")

    # Здесь можно добавить логику для обработки проблем
    # Например, отправка уведомлений, запуск альтернативных процессов и т.д.

    return f"Обработаны проблемы: {issues}"

def process_normal_data(**context):
    """
    Обработка данных при нормальном качестве
    """
    logging.info("Выполняем стандартную обработку данных")

    try:
        # Загрузка данных
        if os.path.exists('/opt/airflow/data/postgres_orders.csv'):
            orders_df = pd.read_csv('/opt/airflow/data/postgres_orders.csv')
        else:
            orders_df = pd.DataFrame()

        if os.path.exists('/opt/airflow/data/processed_deliveries.csv'):
            deliveries_df = pd.read_csv('/opt/airflow/data/processed_deliveries.csv')
        else:
            deliveries_df = pd.DataFrame()

        # Объединение и обработка данных
        if not orders_df.empty and not deliveries_df.empty:
            # Merge данных по order_id
            merged_df = pd.merge(
                orders_df,
                deliveries_df,
                on='order_id',
                how='left'
            )

            # Расчет метрик
            metrics = {
                'total_orders': len(merged_df),
                'completed_orders': len(merged_df[merged_df['order_status'] == 'completed']),
                'delivered_orders': len(merged_df[merged_df['delivery_status'] == 'delivered']),
                'average_order_value': float(merged_df['total_amount'].mean()) if not merged_df.empty else 0
            }

            # Сохранение результатов
            merged_df.to_csv('/opt/airflow/data/final_processed_data.csv', index=False)

            logging.info(f"Обработка завершена. Метрики: {metrics}")
            context['task_instance'].xcom_push(key='processing_metrics', value=metrics)

            return f"Успешно обработано {len(merged_df)} записей"
        else:
            return "Нет данных для обработки"

    except Exception as e:
        logging.error(f"Ошибка при обработке данных: {str(e)}")
        raise

def generate_report(**context):
    """
    Генерация финального отчета
    """
    logging.info("Генерируем финальный отчет")

    metrics = context['task_instance'].xcom_pull(key='processing_metrics')

    report = f"""
    === ОТЧЕТ ПО ОБРАБОТКЕ ДАННЫХ ===
    Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

    Метрики обработки:
    - Всего заказов: {metrics.get('total_orders', 0) if metrics else 0}
    - Завершенных заказов: {metrics.get('completed_orders', 0) if metrics else 0}
    - Доставленных заказов: {metrics.get('delivered_orders', 0) if metrics else 0}
    - Средняя стоимость заказа: {metrics.get('average_order_value', 0) if metrics else 0:.2f}

    Статус: УСПЕШНО ЗАВЕРШЕНО
    ================================
    """

    # Сохранение отчета
    with open('/opt/airflow/data/processing_report.txt', 'w') as f:
        f.write(report)

    logging.info(report)
    return "Отчет сгенерирован успешно"

# Определение задач DAG

# Начало пайплайна
start = DummyOperator(
    task_id='start',
    dag=dag
)

# Чтение данных из PostgreSQL
read_postgres = PythonOperator(
    task_id='read_postgres_data',
    python_callable=read_postgres_data,
    dag=dag,
    provide_context=True
)

# Чтение CSV файлов
read_csv = PythonOperator(
    task_id='read_csv_data',
    python_callable=read_csv_data,
    dag=dag,
    provide_context=True
)

# Анализ качества данных и ветвление
check_data_quality = BranchPythonOperator(
    task_id='analyze_data_quality',
    python_callable=analyze_data_quality,
    dag=dag,
    provide_context=True
)

# Обработка проблем с качеством данных
handle_issues = PythonOperator(
    task_id='handle_data_quality_issues',
    python_callable=handle_quality_issues,
    dag=dag,
    provide_context=True
)

# Нормальная обработка данных
process_data = PythonOperator(
    task_id='process_normal_flow',
    python_callable=process_normal_data,
    dag=dag,
    provide_context=True
)

# Объединение веток
join_branches = DummyOperator(
    task_id='join_branches',
    dag=dag,
    trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS
)

# Генерация отчета
create_report = PythonOperator(
    task_id='generate_report',
    python_callable=generate_report,
    dag=dag,
    provide_context=True
)

# Email уведомление об успешном завершении
send_success_email = EmailOperator(
    task_id='send_success_email',
    to=['larichevns@gmail.com'],
    subject='Пайплайн обработки данных завершен успешно',
    html_content="""
    <h3>Пайплайн обработки данных завершен</h3>
    <p>Дата выполнения: {{ ds }}</p>
    <p>Время выполнения: {{ execution_date }}</p>
    <p>Статус: <b style="color: green;">УСПЕШНО</b></p>
    <p>Подробности можно посмотреть в Airflow UI.</p>
    """,
    dag=dag,
    trigger_rule=TriggerRule.ALL_SUCCESS
)

# Email уведомление об ошибке
send_failure_email = EmailOperator(
    task_id='send_failure_email',
    to=['larichevns@gmail.com'],
    subject='ОШИБКА в пайплайне обработки данных',
    html_content="""
    <h3 style="color: red;">Ошибка в пайплайне обработки данных</h3>
    <p>Дата выполнения: {{ ds }}</p>
    <p>Время выполнения: {{ execution_date }}</p>
    <p>Статус: <b style="color: red;">ОШИБКА</b></p>
    <p>Требуется проверка в Airflow UI.</p>
    """,
    dag=dag,
    trigger_rule=TriggerRule.ONE_FAILED
)

# Конец пайплайна
end = DummyOperator(
    task_id='end',
    dag=dag,
    trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS
)

# Определение зависимостей
start >> [read_postgres, read_csv] >> check_data_quality
check_data_quality >> [handle_issues, process_data]
[handle_issues, process_data] >> join_branches >> create_report
create_report >> [send_success_email, send_failure_email] >> end