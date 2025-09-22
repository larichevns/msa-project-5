# Гайд по созданию демонстрационных материалов

## Варианты создания демонстрации

### Вариант 1: Скриншоты (Рекомендуется)

#### Что нужно заскриншотить:

1. **Запуск Docker контейнеров**
   ```bash
   docker-compose ps
   ```
   Покажет все запущенные контейнеры

2. **Исходные данные лояльности в БД**
   ```bash
   docker exec results-postgresdb-1 psql -U postgres -d productsdb -c "SELECT * FROM loyality_data;"
   ```

3. **Запуск Spring Batch приложения**
   ```bash
   docker-compose up app
   ```
   Захватите логи выполнения с обработкой продуктов

4. **Результаты в таблице products**
   ```bash
   docker exec results-postgresdb-1 psql -U postgres -d productsdb -c "SELECT * FROM products ORDER BY productId;"
   ```

5. **Метаданные выполнения job**
   ```bash
   docker exec results-postgresdb-1 psql -U postgres -d productsdb -c "SELECT job_execution_id, status, start_time, end_time FROM BATCH_JOB_EXECUTION;"
   ```

#### Как делать скриншоты на Mac:
- **Весь экран**: Cmd + Shift + 3
- **Выбранная область**: Cmd + Shift + 4
- **Окно терминала**: Cmd + Shift + 4, затем пробел и клик на окно

### Вариант 2: Видео запись

#### Инструменты для Mac:

1. **QuickTime Player** (встроенный):
   - Откройте QuickTime Player
   - Файл → Новая запись экрана
   - Выберите область для записи
   - Запишите весь процесс запуска

2. **OBS Studio** (бесплатный):
   - Скачайте с https://obsproject.com
   - Настройте захват экрана
   - Запишите демонстрацию

3. **Командная строка** (встроенный):
   ```bash
   # Запись экрана через терминал
   screencapture -v recording.mov
   ```

#### Сценарий для видео (3-5 минут):

1. **Вступление** (10 сек)
   - Покажите структуру проекта
   - `ls -la task-4/results/`

2. **Запуск инфраструктуры** (30 сек)
   - `docker-compose up -d postgresdb`
   - `docker-compose ps`

3. **Инициализация БД** (30 сек)
   - Выполнение SQL скрипта
   - Проверка таблиц

4. **Запуск ETL** (1 мин)
   - `docker-compose up app`
   - Показать логи обработки

5. **Проверка результатов** (30 сек)
   - Запросы к БД
   - Демонстрация обновленных данных

### Вариант 3: Автоматический скрипт демонстрации

Создайте файл `demo.sh`:

```bash
#!/bin/bash

echo "=== SPRING BATCH ETL DEMO ==="
echo ""
echo "Step 1: Checking Docker containers..."
docker-compose ps
sleep 2

echo ""
echo "Step 2: Initial loyalty data..."
docker exec results-postgresdb-1 psql -U postgres -d productsdb -c "SELECT * FROM loyality_data;"
sleep 2

echo ""
echo "Step 3: Running Spring Batch ETL..."
docker-compose up app
sleep 2

echo ""
echo "Step 4: Checking results..."
docker exec results-postgresdb-1 psql -U postgres -d productsdb -c "SELECT * FROM products ORDER BY productId;"
sleep 2

echo ""
echo "Step 5: Job execution status..."
docker exec results-postgresdb-1 psql -U postgres -d productsdb -c "SELECT job_execution_id, status, start_time, end_time FROM BATCH_JOB_EXECUTION;"

echo ""
echo "=== DEMO COMPLETED SUCCESSFULLY ==="
```

Запустите и запишите вывод:
```bash
chmod +x demo.sh
./demo.sh | tee demo-output.txt
```

### Вариант 4: Asciinema (для терминала)

1. **Установка**:
   ```bash
   brew install asciinema
   ```

2. **Запись**:
   ```bash
   asciinema rec demo.cast
   # Выполните все команды демонстрации
   # Ctrl+D для завершения записи
   ```

3. **Воспроизведение**:
   ```bash
   asciinema play demo.cast
   ```

4. **Конвертация в GIF**:
   ```bash
   # Установите svg-term
   npm install -g svg-term-cli

   # Конвертируйте в SVG/GIF
   svg-term --cast=demo.cast --out=demo.svg
   ```

## Рекомендуемый набор скриншотов

Создайте папку `screenshots/` и сохраните:

1. `01-docker-ps.png` - Запущенные контейнеры
2. `02-initial-data.png` - Исходные данные лояльности
3. `03-batch-logs.png` - Логи выполнения Spring Batch
4. `04-products-result.png` - Результаты в таблице products
5. `05-job-status.png` - Статус выполнения job

## Оформление для презентации

### Создайте README с картинками:

```markdown
# Демонстрация работы Spring Batch ETL

## 1. Запуск инфраструктуры
![Docker Containers](screenshots/01-docker-ps.png)

## 2. Исходные данные
![Initial Data](screenshots/02-initial-data.png)

## 3. Процесс ETL
![Batch Processing](screenshots/03-batch-logs.png)

## 4. Результаты обработки
![Results](screenshots/04-products-result.png)

## 5. Статус выполнения
![Job Status](screenshots/05-job-status.png)
```

## Быстрая команда для всех скриншотов

```bash
# Создайте скрипт capture-demo.sh
#!/bin/bash

echo "Capturing demo screenshots..."
echo "Please position your terminal window and press Enter after each step"

echo "1. Docker containers status..."
docker-compose ps
read -p "Press Enter after taking screenshot..."

echo "2. Initial loyalty data..."
docker exec results-postgresdb-1 psql -U postgres -d productsdb -c "SELECT * FROM loyality_data;"
read -p "Press Enter after taking screenshot..."

echo "3. Running ETL (this will take a moment)..."
docker-compose up app
read -p "Press Enter after taking screenshot..."

echo "4. Final results..."
docker exec results-postgresdb-1 psql -U postgres -d productsdb -c "SELECT * FROM products ORDER BY productId;"
read -p "Press Enter after taking screenshot..."

echo "5. Job execution metadata..."
docker exec results-postgresdb-1 psql -U postgres -d productsdb -c "SELECT job_execution_id, status, start_time, end_time FROM BATCH_JOB_EXECUTION;"
read -p "Press Enter after taking screenshot..."

echo "Demo capture completed!"
```

## Альтернатива: Использование Docker Desktop

Если у вас установлен Docker Desktop:
1. Откройте Docker Desktop
2. Перейдите в Containers
3. Найдите results-postgresdb-1 и results-app-1
4. Сделайте скриншот интерфейса с логами

## Финальная проверка

Убедитесь, что на скриншотах/видео видно:
- ✅ Запущенные контейнеры
- ✅ Исходные данные (Loyality_off в CSV, Loyality_on в БД)
- ✅ Процесс обработки (логи с "Processing product...")
- ✅ Результаты (все продукты с Loyality_on)
- ✅ Успешный статус job (COMPLETED)

## Сохранение результатов

1. Создайте папку для демо-материалов:
   ```bash
   mkdir -p task-4/results/demo
   ```

2. Сохраните все скриншоты/видео в эту папку

3. Добавьте в основной README ссылку:
   ```markdown
   ## Демонстрация
   См. папку [demo/](demo/) для скриншотов и видео работы решения.
   ```