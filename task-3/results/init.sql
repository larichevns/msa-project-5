-- Create tables for transportation system

CREATE TABLE IF NOT EXISTS clients (
    client_id SERIAL PRIMARY KEY,
    client_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(50),
    address TEXT,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS drivers (
    driver_id SERIAL PRIMARY KEY,
    driver_name VARCHAR(255) NOT NULL,
    license_number VARCHAR(50) UNIQUE NOT NULL,
    phone VARCHAR(50),
    email VARCHAR(255),
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vehicles (
    vehicle_id SERIAL PRIMARY KEY,
    vehicle_number VARCHAR(50) UNIQUE NOT NULL,
    vehicle_type VARCHAR(100),
    capacity_kg DECIMAL(10,2),
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS shipments (
    shipment_id SERIAL PRIMARY KEY,
    client_id INTEGER REFERENCES clients(client_id),
    driver_id INTEGER REFERENCES drivers(driver_id),
    vehicle_id INTEGER REFERENCES vehicles(vehicle_id),
    origin_city VARCHAR(255),
    destination_city VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending',
    total_distance_km DECIMAL(10,2),
    total_cost DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS shipment_events (
    event_id SERIAL PRIMARY KEY,
    shipment_id INTEGER REFERENCES shipments(shipment_id),
    event_type VARCHAR(50),
    event_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    location VARCHAR(255),
    description TEXT
);

-- Insert sample data
INSERT INTO clients (client_name, email, phone, address, active) VALUES
('ООО Логистика', 'logistics@example.com', '+7-495-123-4567', 'Москва, ул. Ленина, 1', true),
('ЗАО ТрансСервис', 'trans@example.com', '+7-812-234-5678', 'Санкт-Петербург, Невский пр., 10', true),
('ИП Иванов', 'ivanov@example.com', '+7-916-345-6789', 'Екатеринбург, ул. Мира, 5', true);

INSERT INTO drivers (driver_name, license_number, phone, email, active) VALUES
('Петров П.П.', 'AB123456', '+7-916-111-2222', 'petrov@example.com', true),
('Сидоров С.С.', 'CD789012', '+7-916-222-3333', 'sidorov@example.com', true),
('Козлов К.К.', 'EF345678', '+7-916-333-4444', 'kozlov@example.com', true);

INSERT INTO vehicles (vehicle_number, vehicle_type, capacity_kg, active) VALUES
('А123БВ77', 'Фургон', 5000, true),
('Е456ГД99', 'Грузовик', 10000, true),
('К789ЕЖ50', 'Фургон', 3000, true);

-- Generate sample shipments for yesterday
INSERT INTO shipments (client_id, driver_id, vehicle_id, origin_city, destination_city, status, total_distance_km, total_cost, created_at)
SELECT
    (random() * 2 + 1)::int as client_id,
    (random() * 2 + 1)::int as driver_id,
    (random() * 2 + 1)::int as vehicle_id,
    cities.origin,
    cities.destination,
    statuses.status,
    (random() * 1000 + 100)::numeric(10,2) as distance,
    (random() * 50000 + 5000)::numeric(10,2) as cost,
    CURRENT_DATE - INTERVAL '1 day' + (random() * INTERVAL '24 hours')
FROM
    (VALUES ('Москва', 'Санкт-Петербург'), ('Екатеринбург', 'Новосибирск'), ('Казань', 'Самара')) as cities(origin, destination),
    (VALUES ('delivered'), ('in_transit'), ('pending')) as statuses(status),
    generate_series(1, 50);

-- Generate sample events for yesterday
INSERT INTO shipment_events (shipment_id, event_type, event_timestamp, location, description)
SELECT
    s.shipment_id,
    event_types.type,
    s.created_at + (random() * INTERVAL '2 hours'),
    locations.city,
    'Событие ' || event_types.type
FROM
    shipments s,
    (VALUES ('pickup'), ('departure'), ('arrival'), ('delivery')) as event_types(type),
    (VALUES ('Москва'), ('Тверь'), ('Новгород'), ('Санкт-Петербург')) as locations(city)
WHERE s.created_at > CURRENT_DATE - INTERVAL '2 days'
LIMIT 200;