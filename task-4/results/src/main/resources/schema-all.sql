-- Таблица продуктов
CREATE TABLE IF NOT EXISTS products  (
    productId BIGINT NOT NULL,
    productSku BIGINT NOT NULL,
    productName VARCHAR(50),
    productAmount BIGINT,
    productData VARCHAR(120),
    PRIMARY KEY (productId, productSku)
);

-- Таблица данных лояльности
CREATE TABLE IF NOT EXISTS loyality_data  (
    productSku BIGINT NOT NULL PRIMARY KEY,
    loyalityData VARCHAR(120)
);

-- Загрузка начальных данных лояльности
INSERT INTO loyality_data (productSku, loyalityData) VALUES
    (20001, 'Loyality_on'),
    (30001, 'Loyality_on'),
    (50001, 'Loyality_on'),
    (60001, 'Loyality_on')
ON CONFLICT (productSku) DO NOTHING;