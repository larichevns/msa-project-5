# План имплементации решения на базе Kubernetes CronJob

## Общая информация
**Цель**: Автоматизация генерации CSV прайс-листов для B2B клиентов
**Технологии**: Kubernetes CronJob, Python, PostgreSQL, S3/MinIO
**Время реализации**: 3-4 дня

## Фаза 1: Подготовка инфраструктуры

### 1.1 Настройка базы данных
```sql
-- Создание индексов для оптимизации JOIN операций
CREATE INDEX idx_client_prices_client_id ON client_prices(client_id);
CREATE INDEX idx_client_prices_product_id ON client_prices(product_id);
CREATE INDEX idx_products_category_id ON products(category_id);

-- Создание view для упрощения выборки
CREATE VIEW v_client_price_list AS
SELECT
    c.client_id,
    c.client_name,
    c.client_email,
    p.product_id,
    p.product_name,
    p.product_sku,
    cat.category_name,
    COALESCE(cp.custom_price, p.base_price) as final_price,
    p.stock_quantity,
    p.is_available
FROM clients c
CROSS JOIN products p
LEFT JOIN client_prices cp ON c.client_id = cp.client_id AND p.product_id = cp.product_id
LEFT JOIN categories cat ON p.category_id = cat.category_id
WHERE p.is_available = true;
```

### 1.2 Настройка S3/MinIO
```yaml
# minio-deployment.yaml
apiVersion: v1
kind: Secret
metadata:
  name: minio-secret
type: Opaque
data:
  access-key: <base64-encoded-access-key>
  secret-key: <base64-encoded-secret-key>

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: minio
spec:
  replicas: 1
  selector:
    matchLabels:
      app: minio
  template:
    metadata:
      labels:
        app: minio
    spec:
      containers:
      - name: minio
        image: minio/minio:latest
        args:
        - server
        - /data
        env:
        - name: MINIO_ACCESS_KEY
          valueFrom:
            secretKeyRef:
              name: minio-secret
              key: access-key
        - name: MINIO_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: minio-secret
              key: secret-key
        volumeMounts:
        - name: storage
          mountPath: /data
      volumes:
      - name: storage
        persistentVolumeClaim:
          claimName: minio-pvc
```

### 1.3 Создание ConfigMap и Secrets
```yaml
# config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: pricelist-config
data:
  database_host: "postgres-service"
  database_name: "ecommerce"
  s3_endpoint: "http://minio-service:9000"
  s3_bucket: "price-lists"
  email_smtp_host: "smtp.gmail.com"
  email_smtp_port: "587"

---
# secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: pricelist-secrets
type: Opaque
data:
  database_user: <base64>
  database_password: <base64>
  s3_access_key: <base64>
  s3_secret_key: <base64>
  email_user: <base64>
  email_password: <base64>
```

## Фаза 2: Разработка приложения

### 2.1 Структура проекта
```
price-list-generator/
├── Dockerfile
├── requirements.txt
├── src/
│   ├── main.py
│   ├── database.py
│   ├── csv_generator.py
│   ├── s3_uploader.py
│   ├── email_sender.py
│   └── metrics.py
├── tests/
│   └── test_generator.py
└── k8s/
    ├── cronjob.yaml
    ├── configmap.yaml
    └── secrets.yaml
```

### 2.2 Python приложение
```python
# requirements.txt
psycopg2-binary==2.9.9
pandas==2.1.3
boto3==1.29.7
prometheus-client==0.19.0
python-dotenv==1.0.0
jinja2==3.1.2

# main.py - основная логика
import os
import logging
from datetime import datetime
import pandas as pd
from database import DatabaseConnection
from csv_generator import CSVGenerator
from s3_uploader import S3Uploader
from email_sender import EmailSender
from metrics import MetricsCollector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    metrics = MetricsCollector()

    try:
        # Инициализация компонентов
        db = DatabaseConnection()
        generator = CSVGenerator()
        uploader = S3Uploader()
        email = EmailSender()

        # Получение списка клиентов
        clients = db.get_active_clients()

        for client in clients:
            try:
                # Генерация прайс-листа для клиента
                data = db.get_client_prices(client['client_id'])
                csv_file = generator.generate(data, client)

                # Загрузка в S3
                url = uploader.upload(csv_file, client['client_id'])

                # Отправка email
                email.send_notification(client['email'], url)

                metrics.record_success(client['client_id'])

            except Exception as e:
                logger.error(f"Error processing client {client['client_id']}: {e}")
                metrics.record_failure(client['client_id'])

        metrics.push_to_prometheus()

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    main()
```

### 2.3 Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копирование зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода
COPY src/ ./src/

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s \
    CMD curl -f http://localhost:8080/health || exit 1

# Запуск приложения
CMD ["python", "-m", "src.main"]
```

## Фаза 3: Deployment в Kubernetes

### 3.1 CronJob манифест
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: price-list-generator
  namespace: default
spec:
  schedule: "0 6 * * *"  # Каждый день в 6:00 UTC
  concurrencyPolicy: Forbid  # Не запускать новый, если старый еще работает
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      backoffLimit: 3  # Количество попыток при сбое
      activeDeadlineSeconds: 3600  # Максимум 1 час на выполнение
      template:
        metadata:
          annotations:
            prometheus.io/scrape: "true"
            prometheus.io/port: "8080"
        spec:
          restartPolicy: OnFailure
          containers:
          - name: price-list-generator
            image: your-registry/price-list-generator:v1.0.0
            imagePullPolicy: Always
            env:
            - name: DATABASE_HOST
              valueFrom:
                configMapKeyRef:
                  name: pricelist-config
                  key: database_host
            - name: DATABASE_USER
              valueFrom:
                secretKeyRef:
                  name: pricelist-secrets
                  key: database_user
            - name: DATABASE_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: pricelist-secrets
                  key: database_password
            - name: S3_ACCESS_KEY
              valueFrom:
                secretKeyRef:
                  name: pricelist-secrets
                  key: s3_access_key
            - name: S3_SECRET_KEY
              valueFrom:
                secretKeyRef:
                  name: pricelist-secrets
                  key: s3_secret_key
            resources:
              requests:
                memory: "128Mi"
                cpu: "100m"
              limits:
                memory: "512Mi"
                cpu: "500m"
            volumeMounts:
            - name: temp
              mountPath: /tmp
          volumes:
          - name: temp
            emptyDir: {}
```

### 3.2 Мониторинг и алерты
```yaml
# prometheus-rules.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: pricelist-alerts
spec:
  groups:
  - name: pricelist
    rules:
    - alert: PriceListGenerationFailed
      expr: increase(cronjob_failures_total[1d]) > 0
      for: 5m
      annotations:
        summary: "Price list generation failed"
        description: "The price list generation job has failed {{ $value }} times in the last day"

    - alert: PriceListGenerationSlow
      expr: cronjob_execution_duration_seconds > 1800
      for: 5m
      annotations:
        summary: "Price list generation is slow"
        description: "Price list generation took {{ $value }} seconds (threshold: 30 minutes)"
```

### 3.3 Grafana Dashboard
```json
{
  "dashboard": {
    "title": "Price List Generator",
    "panels": [
      {
        "title": "Execution Status",
        "targets": [
          {
            "expr": "sum(rate(cronjob_executions_total[5m])) by (status)"
          }
        ]
      },
      {
        "title": "Processing Time",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, cronjob_execution_duration_seconds)"
          }
        ]
      },
      {
        "title": "Files Generated",
        "targets": [
          {
            "expr": "sum(increase(cronjob_files_generated_total[1d]))"
          }
        ]
      }
    ]
  }
}
```

## Фаза 4: Тестирование и оптимизация 

### 4.1 Ручное тестирование
```bash
# Создание тестового Job для проверки
kubectl create job --from=cronjob/price-list-generator test-run

# Проверка логов
kubectl logs job/test-run

# Проверка метрик
kubectl port-forward service/prometheus 9090:9090
# Открыть http://localhost:9090
```

### 4.2 Нагрузочное тестирование
```python
# load_test.py
import concurrent.futures
from database import DatabaseConnection

def test_query_performance(client_id):
    db = DatabaseConnection()
    start = time.time()
    data = db.get_client_prices(client_id)
    duration = time.time() - start
    return len(data), duration

# Параллельное выполнение для всех клиентов
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(test_query_performance, i) for i in range(1, 101)]
    results = [f.result() for f in futures]
```

### 4.3 Оптимизация производительности
1. **Batch processing**: Обработка клиентов пачками
2. **Connection pooling**: Использование пула соединений к БД
3. **Parallel uploads**: Параллельная загрузка в S3
4. **Query optimization**: Оптимизация SQL запросов

## Фаза 5: Production Deployment

### 5.1 CI/CD Pipeline
```yaml
# .gitlab-ci.yml
stages:
  - build
  - test
  - deploy

build:
  stage: build
  script:
    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA

test:
  stage: test
  script:
    - python -m pytest tests/

deploy:
  stage: deploy
  script:
    - kubectl set image cronjob/price-list-generator \
        price-list-generator=$CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
```

### 5.2 Rollback план
```bash
# Сохранение текущей версии
kubectl get cronjob price-list-generator -o yaml > backup.yaml

# Rollback при необходимости
kubectl apply -f backup.yaml
```