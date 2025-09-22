# Task 6: Spring Batch с трейсингом запросов

## Обзор

Данный проект демонстрирует интеграцию распределенного трейсинга в Spring Batch приложение с REST API для запуска ETL-задач.

## Архитектура

### Компоненты системы

1. **Spring Batch Application** - REST API для запуска ETL-задач
2. **Python Client** - Клиентское приложение для вызова API
3. **PostgreSQL** - База данных для Spring Batch метаданных и данных
4. **ELK Stack** - Elasticsearch, Logstash, Kibana для логирования и трейсинга

### Ключевые особенности

#### 1. Распределенный трейсинг
- **Micrometer Tracing** с Brave backend
- Генерация `traceId` и `spanId` для каждого запроса
- Передача trace контекста через HTTP headers
- Логирование с trace информацией

#### 2. API Endpoints
- `POST /api/jobs/trigger` - Запуск Spring Batch job
- `GET /api/jobs/status` - Проверка состояния API

#### 3. Логирование
- JSON формат логов для лучшей интеграции с ELK
- Включение `traceId`, `spanId`, `URI`, `method` в каждое сообщение
- Прямая отправка логов в Logstash через TCP

## Быстрый старт

### 1. Запуск системы

```bash
# Запуск базы данных
docker-compose up -d postgresdb

# Запуск приложения
docker-compose up -d app

# Запуск ELK стека (опционально)
docker-compose up -d elasticsearch logstash kibana
```

### 2. Тестирование API

```bash
# Проверка состояния
curl http://localhost:8082/api/jobs/status

# Запуск job
curl -X POST http://localhost:8082/api/jobs/trigger
```

### 3. Использование Python клиента

```bash
cd client
python3 job_client.py
```

## Демонстрация трейсинга

### Структура трейсинга

Каждый запрос генерирует уникальные идентификаторы:

```json
{
  "traceId": "68d151d808770f20f4b3bc3bbc498ea4",
  "spanId": "f4b3bc3bbc498ea4",
  "service": "Spring Batch ETL Service",
  "status": "healthy",
  "timestamp": 1758548434194
}
```

### Логирование с трейсингом

Пример лога с trace информацией:

```json
{
  "@timestamp": "2025-09-22T13:40:40.823830547Z",
  "level": "INFO",
  "logger_name": "com.example.batchprocessing.controller.JobController",
  "thread_name": "http-nio-8080-exec-6",
  "message": "Spring Batch job completed successfully. JobExecutionId: 1, TraceId: 68d151d808770f20f4b3bc3bbc498ea4",
  "spanId": "f4b3bc3bbc498ea4",
  "service": "spring-batch-etl",
  "environment": "production",
  "host": "8594368cdb13"
}
```

### Python клиент с трейсингом

Клиент генерирует собственные trace ID и логирует корреляцию:

```
2025-09-22 17:41:01,435 - __main__ - INFO - [c714cf2509404e71] - Server trace correlation: ClientTrace=c714cf2509404e71, ServerTrace=68d151ed2fc8441f2972640ff931f58d
```

## Технические детали

### Используемые технологии

- **Spring Boot 3.5.3** с Spring Batch
- **Micrometer Tracing** для распределенного трейсинга
- **Brave** как бэкенд для трейсинга
- **Logback** с JSON кодировщиком
- **PostgreSQL** для данных
- **ELK Stack** для логирования

### Конфигурация трейсинга

```properties
# Включение трейсинга
management.tracing.sampling.probability=1.0

# Отключение автозапуска jobs
spring.batch.job.enabled=false

# Конфигурация логирования с trace
logging.pattern.console=%d{yyyy-MM-dd HH:mm:ss} [%thread] %-5level [%X{traceId:-},%X{spanId:-}] %logger{36} - %msg%n
```

### Архитектура JobController

```java
@RestController
@RequestMapping("/api/jobs")
public class JobController {

    @PostMapping("/trigger")
    public ResponseEntity<Map<String, Object>> triggerJob(HttpServletRequest request) {
        // Получение trace информации
        String traceId = tracer.currentSpan().context().traceId();
        String spanId = tracer.currentSpan().context().spanId();

        // Добавление в MDC для логирования
        MDC.put("traceId", traceId);
        MDC.put("spanId", spanId);

        // Запуск job с trace параметрами
        JobParameters jobParameters = new JobParametersBuilder()
            .addString("traceId", traceId)
            .addString("spanId", spanId)
            .toJobParameters();

        // Возврат response с trace информацией
        response.put("traceId", traceId);
        response.put("spanId", spanId);
    }
}
```

## Результаты выполнения

### Успешные запуски

1. API health check - возвращает trace информацию
2. Запуск Spring Batch jobs через REST API
3. Генерация уникальных traceId и spanId
4. Логирование с полным trace контекстом
5. Python клиент с собственным трейсингом
6. Корреляция между клиентом и сервером

### Примеры выполнения

**Health Check:**
```bash
curl http://localhost:8082/api/jobs/status
{
  "traceId": "68d151d2028eabb266b9b59ffc5a4ea1",
  "spanId": "66b9b59ffc5a4ea1",
  "service": "Spring Batch ETL Service",
  "status": "healthy",
  "timestamp": 1758548434194
}
```

**Job Trigger:**
```bash
curl -X POST http://localhost:8082/api/jobs/trigger
{
  "traceId": "68d151d808770f20f4b3bc3bbc498ea4",
  "spanId": "f4b3bc3bbc498ea4",
  "jobExecutionId": 1,
  "method": "POST",
  "message": "Job triggered successfully",
  "uri": "/api/jobs/trigger",
  "status": "success",
  "timestamp": 1758548440823
}
```

**Python Client Output:**
```
Spring Batch Job Client with Tracing
========================================

1. Checking API health...
✅ API is healthy

2. Triggering Spring Batch jobs...

--- Job 1 ---
✅ Job triggered successfully
   Client Trace ID: c714cf2509404e71
   Job Execution ID: 2
   Server Trace ID: 68d151ed2fc8441f2972640ff931f58d
   Duration: 0.04s
```

## Заключение

Проект успешно демонстрирует:
- Интеграцию распределенного трейсинга в Spring Batch приложение
- REST API для управления ETL-задачами
- Клиент-серверную корреляцию через trace ID
- Структурированное логирование с trace контекстом
- Готовность к интеграции с мониторинговыми системами

Все компоненты системы логируют trace информацию, что обеспечивает полную видимость распределенных операций.