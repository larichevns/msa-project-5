-- Создание таблиц с тестовыми данными

-- Таблица заказов
CREATE TABLE IF NOT EXISTS orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INTEGER,
    order_date DATE,
    total_amount DECIMAL(10, 2),
    status VARCHAR(50)
);

-- Таблица платежей
CREATE TABLE IF NOT EXISTS payments (
    payment_id SERIAL PRIMARY KEY,
    order_id INTEGER,
    payment_date DATE,
    amount DECIMAL(10, 2),
    payment_method VARCHAR(50),
    status VARCHAR(50)
);

-- Таблица пользователей
CREATE TABLE IF NOT EXISTS customers (
    customer_id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100),
    registration_date DATE,
    city VARCHAR(100),
    total_spent DECIMAL(10, 2)
);

-- Вставка тестовых данных
INSERT INTO customers (name, email, registration_date, city, total_spent) VALUES
    ('Иван Иванов', 'ivan@example.com', '2023-01-15', 'Москва', 15000.00),
    ('Петр Петров', 'petr@example.com', '2023-02-20', 'Санкт-Петербург', 25000.00),
    ('Мария Сидорова', 'maria@example.com', '2023-03-10', 'Новосибирск', 8000.00),
    ('Елена Козлова', 'elena@example.com', '2023-04-05', 'Екатеринбург', 12000.00),
    ('Алексей Смирнов', 'alexey@example.com', '2023-05-12', 'Казань', 30000.00);

INSERT INTO orders (customer_id, order_date, total_amount, status) VALUES
    (1, '2024-01-10', 5000.00, 'completed'),
    (2, '2024-01-15', 8000.00, 'completed'),
    (3, '2024-01-20', 3000.00, 'processing'),
    (4, '2024-01-25', 6000.00, 'completed'),
    (5, '2024-02-01', 12000.00, 'completed'),
    (1, '2024-02-05', 4500.00, 'shipped'),
    (2, '2024-02-10', 7500.00, 'processing');

INSERT INTO payments (order_id, payment_date, amount, payment_method, status) VALUES
    (1, '2024-01-10', 5000.00, 'credit_card', 'success'),
    (2, '2024-01-15', 8000.00, 'debit_card', 'success'),
    (3, '2024-01-20', 3000.00, 'paypal', 'pending'),
    (4, '2024-01-25', 6000.00, 'credit_card', 'success'),
    (5, '2024-02-01', 12000.00, 'bank_transfer', 'success');