# C4 Диаграммы архитектуры с Spring Batch

## Уровень 1: Контекст системы (System Context)

```mermaid
graph TB
    subgraph "TradeWare"
        WMS[Система управления складом]
    end

    User[Сотрудник склада]
    Partner[Партнерские системы]
    GCS[Google Cloud Storage]

    User -->|Загружает CSV отчеты| WMS
    User -->|Просматривает остатки| WMS
    WMS -->|Хранит файлы| GCS
    Partner -->|Запрашивает данные| WMS
    WMS -->|Предоставляет API| Partner

    style WMS fill:#1168BD,stroke:#333,stroke-width:4px,color:#fff
    style User fill:#08427B,stroke:#333,stroke-width:2px,color:#fff
    style Partner fill:#08427B,stroke:#333,stroke-width:2px,color:#fff
    style GCS fill:#999999,stroke:#333,stroke-width:2px,color:#fff
```

## Уровень 2: Контейнеры (Container Diagram)

```mermaid
graph TB
    subgraph "Google Cloud Platform"
        GCS[Google Cloud Storage<br/>Хранилище файлов]
        PostgresMain[(PostgreSQL<br/>Основная БД)]
        PostgresBatch[(PostgreSQL<br/>БД Spring Batch<br/>метаданных)]
    end

    subgraph "Backend GCP/ComputeEngine"
        WebApp[Angular Web Application<br/>Container: JS, Angular]
        JavaApp[Java Monolith<br/>Container: WildFly/Java 11]
        BatchApp[Spring Batch ETL<br/>Container: Spring Boot/Java 11]
    end

    User[Сотрудник склада]

    User -->|Использует| WebApp
    WebApp -->|REST API| JavaApp
    JavaApp -->|Запускает ETL| BatchApp
    BatchApp -->|Читает файлы| GCS
    BatchApp -->|Читает/пишет данные| PostgresMain
    BatchApp -->|Сохраняет метаданные| PostgresBatch
    JavaApp -->|Читает/пишет| PostgresMain
    JavaApp -->|Сохраняет файлы| GCS

    style BatchApp fill:#FFB366,stroke:#333,stroke-width:4px,color:#000
    style JavaApp fill:#1168BD,stroke:#333,stroke-width:2px,color:#fff
    style WebApp fill:#1168BD,stroke:#333,stroke-width:2px,color:#fff
    style PostgresMain fill:#336791,stroke:#333,stroke-width:2px,color:#fff
    style PostgresBatch fill:#336791,stroke:#333,stroke-width:2px,color:#fff
    style GCS fill:#4285F4,stroke:#333,stroke-width:2px,color:#fff
```

## Уровень 3: Компоненты Spring Batch (Component Diagram)

```mermaid
graph TB
    subgraph "Spring Batch ETL Application"
        subgraph "Job Configuration"
            JobLauncher[Job Launcher<br/>Запуск задач]
            JobRepo[Job Repository<br/>Метаданные выполнения]
            Job[Import Product Job<br/>Основная задача]
        end

        subgraph "Step Components"
            Step[Step 1: Process Products<br/>Шаг обработки]
            Reader[FlatFileItemReader<br/>Чтение CSV]
            Processor[ProductItemProcessor<br/>Обогащение данных]
            Writer[JdbcBatchItemWriter<br/>Запись в БД]
        end

        subgraph "Support Components"
            Listener[JobCompletionListener<br/>Уведомления]
            TxManager[Transaction Manager<br/>Управление транзакциями]
            DataSource[Data Source<br/>Пул соединений]
        end
    end

    subgraph "External Systems"
        CSV[CSV Files<br/>product-data.csv]
        LoyaltyDB[(Loyalty Data<br/>loyality_data table)]
        ProductDB[(Products<br/>products table)]
        MetaDB[(Batch Metadata<br/>BATCH_* tables)]
    end

    JobLauncher --> Job
    Job --> Step
    Job --> Listener
    Step --> Reader
    Step --> Processor
    Step --> Writer
    Step --> TxManager

    Reader --> CSV
    Processor --> LoyaltyDB
    Writer --> ProductDB
    JobRepo --> MetaDB

    DataSource --> LoyaltyDB
    DataSource --> ProductDB
    DataSource --> MetaDB

    style Job fill:#FFB366,stroke:#333,stroke-width:3px
    style Step fill:#85C1F2,stroke:#333,stroke-width:2px
    style Reader fill:#85C1F2,stroke:#333,stroke-width:2px
    style Processor fill:#85C1F2,stroke:#333,stroke-width:2px
    style Writer fill:#85C1F2,stroke:#333,stroke-width:2px
```

## Уровень 4: Последовательность обработки (Sequence Diagram)

```mermaid
sequenceDiagram
    participant U as Сотрудник
    participant W as Web UI
    participant J as Java Monolith
    participant B as Spring Batch
    participant R as ItemReader
    participant P as ItemProcessor
    participant Wr as ItemWriter
    participant DB as PostgreSQL

    U->>W: Загрузить CSV файл
    W->>J: POST /upload
    J->>J: Валидация формата
    J->>B: Запустить Job
    B->>B: Создать JobExecution

    loop Для каждого chunk
        B->>R: Прочитать chunk записей
        R->>R: Парсинг CSV
        R-->>B: List<Product>

        loop Для каждой записи
            B->>P: process(Product)
            P->>DB: SELECT from loyality_data
            DB-->>P: Loyalty данные
            P->>P: Обогатить продукт
            P-->>B: Обработанный Product
        end

        B->>Wr: write(List<Product>)
        Wr->>DB: BATCH INSERT into products
        B->>B: Commit транзакции
    end

    B->>B: Завершить JobExecution
    B-->>J: Статус выполнения
    J-->>W: Результат обработки
    W-->>U: Уведомление
```

## Архитектурные решения

### 1. Chunk-Oriented Processing
- **Размер chunk**: 100-500 записей (настраивается)
- **Преимущества**: Оптимальное использование памяти, транзакционность на уровне chunk
- **Restart**: При сбое обработка продолжается с последнего успешного chunk

### 2. Параллельная обработка
```mermaid
graph LR
    subgraph "Partitioned Step"
        Master[Master Step]
        P1[Partition 1<br/>Records 1-1000]
        P2[Partition 2<br/>Records 1001-2000]
        P3[Partition 3<br/>Records 2001-3000]
        Agg[Aggregator]
    end

    Master --> P1
    Master --> P2
    Master --> P3
    P1 --> Agg
    P2 --> Agg
    P3 --> Agg
```

### 3. Интеграция с существующей системой

```mermaid
graph TB
    subgraph "Current State"
        M1[Монолит<br/>Все функции]
    end

    subgraph "With Spring Batch"
        M2[Монолит<br/>UI + API]
        B1[Spring Batch<br/>ETL обработка]
        M2 -.->|Делегирует ETL| B1
    end

    subgraph "Future State"
        UI[UI Service]
        API[API Gateway]
        ETL[ETL Service<br/>Spring Batch]
        INV[Inventory Service]
        REP[Reporting Service]
    end

    M1 ==> M2
    M2 ==> API
    B1 ==> ETL

    style M1 fill:#FF6B6B,stroke:#333,stroke-width:2px
    style M2 fill:#FFB366,stroke:#333,stroke-width:2px
    style B1 fill:#4ECDC4,stroke:#333,stroke-width:2px
    style ETL fill:#95E77E,stroke:#333,stroke-width:2px
```

### 4. Мониторинг и метрики

```mermaid
graph TB
    subgraph "Spring Batch Monitoring"
        Batch[Spring Batch App]
        Actuator[Spring Boot Actuator<br/>Метрики]
        Micrometer[Micrometer<br/>Сбор метрик]

        subgraph "Metrics"
            M1[job.duration]
            M2[step.duration]
            M3[read.count]
            M4[write.count]
            M5[skip.count]
            M6[failure.count]
        end
    end

    subgraph "Monitoring Stack"
        Prom[Prometheus<br/>Time-series DB]
        Graf[Grafana<br/>Визуализация]
        Alert[AlertManager<br/>Уведомления]
    end

    Batch --> Actuator
    Actuator --> Micrometer
    Micrometer --> M1
    Micrometer --> M2
    Micrometer --> M3
    Micrometer --> M4
    Micrometer --> M5
    Micrometer --> M6

    Micrometer --> Prom
    Prom --> Graf
    Prom --> Alert

    style Batch fill:#FFB366,stroke:#333,stroke-width:2px
    style Prom fill:#E6522C,stroke:#333,stroke-width:2px
    style Graf fill:#F46800,stroke:#333,stroke-width:2px
```

## Потоки данных

### Основной ETL поток
1. **Загрузка файла** → GCS
2. **Запуск Job** → Spring Batch
3. **Чтение CSV** → ItemReader
4. **Обогащение** → ItemProcessor + Loyalty DB
5. **Запись** → ItemWriter + Products DB
6. **Уведомление** → JobCompletionListener

### Поток при ошибке
1. **Обнаружение ошибки** → Exception в процессоре
2. **Skip Policy** → Пропуск проблемной записи
3. **Retry Policy** → Повторная попытка (3 раза)
4. **Rollback** → Откат транзакции chunk
5. **Логирование** → Запись в error_log
6. **Продолжение** → Обработка следующего chunk

## Выводы

Архитектура с Spring Batch обеспечивает:
- ✅ Надежную обработку больших объемов данных
- ✅ Возможность горизонтального масштабирования через партиционирование
- ✅ Механизмы восстановления после сбоев
- ✅ Интеграцию с существующей Java инфраструктурой
- ✅ Путь миграции к микросервисной архитектуре
- ✅ Полный мониторинг и observability