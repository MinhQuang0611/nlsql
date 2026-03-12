-- =============================================================================
-- seed.sql — Seed data for nlsql demo (e-commerce domain)
-- Run via: psql $DATABASE_URL -f db/seeds/seed.sql
--      or: make seed
-- =============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
-- 0. Extensions & settings
-- ─────────────────────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
SET client_min_messages = WARNING;


-- ─────────────────────────────────────────────────────────────────────────────
-- 1. Schema
-- ─────────────────────────────────────────────────────────────────────────────

-- Categories
CREATE TABLE IF NOT EXISTS categories (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    description TEXT
);

-- Products
CREATE TABLE IF NOT EXISTS products (
    id           SERIAL PRIMARY KEY,
    category_id  INT REFERENCES categories(id),
    name         VARCHAR(255) NOT NULL,
    sku          VARCHAR(50)  NOT NULL UNIQUE,
    price        NUMERIC(10,2) NOT NULL,
    cost         NUMERIC(10,2) NOT NULL,
    stock_qty    INT NOT NULL DEFAULT 0,
    is_active    BOOLEAN NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Customers
CREATE TABLE IF NOT EXISTS customers (
    id           SERIAL PRIMARY KEY,
    full_name    VARCHAR(255) NOT NULL,
    email        VARCHAR(255) NOT NULL UNIQUE,
    city         VARCHAR(100),
    country      VARCHAR(100) NOT NULL DEFAULT 'Vietnam',
    segment      VARCHAR(50)  NOT NULL DEFAULT 'retail',  -- retail | wholesale | vip
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Orders
CREATE TABLE IF NOT EXISTS orders (
    id           SERIAL PRIMARY KEY,
    customer_id  INT REFERENCES customers(id),
    status       VARCHAR(50) NOT NULL DEFAULT 'completed', -- pending | completed | cancelled | refunded
    total_amount NUMERIC(12,2) NOT NULL,
    discount     NUMERIC(10,2) NOT NULL DEFAULT 0,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Order items
CREATE TABLE IF NOT EXISTS order_items (
    id          SERIAL PRIMARY KEY,
    order_id    INT REFERENCES orders(id) ON DELETE CASCADE,
    product_id  INT REFERENCES products(id),
    quantity    INT           NOT NULL,
    unit_price  NUMERIC(10,2) NOT NULL,
    subtotal    NUMERIC(12,2) GENERATED ALWAYS AS (quantity * unit_price) STORED
);

-- Daily sales summary (pre-aggregated — useful for fast dashboard queries)
CREATE TABLE IF NOT EXISTS daily_sales (
    date          DATE PRIMARY KEY,
    total_orders  INT           NOT NULL DEFAULT 0,
    total_revenue NUMERIC(14,2) NOT NULL DEFAULT 0,
    total_cost    NUMERIC(14,2) NOT NULL DEFAULT 0,
    avg_order_value NUMERIC(10,2) NOT NULL DEFAULT 0
);


-- ─────────────────────────────────────────────────────────────────────────────
-- 2. Truncate (idempotent re-run)
-- ─────────────────────────────────────────────────────────────────────────────
TRUNCATE order_items, orders, products, customers, categories, daily_sales
    RESTART IDENTITY CASCADE;


-- ─────────────────────────────────────────────────────────────────────────────
-- 3. Categories
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO categories (name, description) VALUES
    ('Electronics',    'Phones, laptops, accessories'),
    ('Clothing',       'Apparel for men, women, kids'),
    ('Home & Kitchen', 'Furniture, appliances, decor'),
    ('Books',          'Fiction, non-fiction, textbooks'),
    ('Sports',         'Equipment, gym wear, outdoor gear');


-- ─────────────────────────────────────────────────────────────────────────────
-- 4. Products (30 rows)
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO products (category_id, name, sku, price, cost, stock_qty) VALUES
-- Electronics
(1, 'iPhone 15 Pro',          'EL-001', 29990000, 22000000, 50),
(1, 'Samsung Galaxy S24',     'EL-002', 22990000, 17000000, 80),
(1, 'MacBook Air M3',         'EL-003', 35990000, 27000000, 30),
(1, 'Sony WH-1000XM5',        'EL-004',  8990000,  5500000, 120),
(1, 'iPad Air 5',             'EL-005', 16490000, 12000000, 60),
(1, 'Logitech MX Master 3',   'EL-006',  2490000,  1500000, 200),
-- Clothing
(2, 'Uniqlo Ultra-Light Down','CL-001',  1290000,   600000, 300),
(2, 'Adidas Ultraboost 23',   'CL-002',  3990000,  2000000, 150),
(2, 'Levi''s 501 Jeans',      'CL-003',  1890000,   900000, 250),
(2, 'Nike Dri-FIT T-Shirt',   'CL-004',   590000,   250000, 500),
(2, 'Zara Blazer Slim',       'CL-005',  2490000,  1100000, 100),
(2, 'H&M Basic Hoodie',       'CL-006',   690000,   300000, 400),
-- Home & Kitchen
(3, 'Philips Air Fryer',      'HK-001',  3490000,  2000000, 80),
(3, 'IKEA KALLAX Shelf',      'HK-002',  2990000,  1400000, 60),
(3, 'Nespresso Vertuo Next',  'HK-003',  4290000,  2500000, 70),
(3, 'Dyson V15 Detect',       'HK-004', 14990000,  9000000, 25),
(3, 'Instant Pot Duo 7-in-1', 'HK-005',  2790000,  1500000, 90),
(3, 'Xiaomi Robot Vacuum',    'HK-006',  7990000,  4500000, 40),
-- Books
(4, 'Atomic Habits',          'BK-001',   189000,    80000, 1000),
(4, 'The Lean Startup',       'BK-002',   229000,    90000, 800),
(4, 'Deep Work',              'BK-003',   199000,    85000, 900),
(4, 'Dune',                   'BK-004',   249000,   100000, 600),
(4, 'Python Crash Course',    'BK-005',   359000,   150000, 500),
(4, 'Designing Data-Intensive Applications', 'BK-006', 589000, 250000, 300),
-- Sports
(5, 'Garmin Forerunner 265',  'SP-001', 12990000,  8000000, 45),
(5, 'Yonex Astrox 88D',       'SP-002',  4290000,  2500000, 70),
(5, 'TRX Suspension Trainer', 'SP-003',  2990000,  1500000, 100),
(5, 'Decathlon Running Shoes','SP-004',  1290000,   600000, 200),
(5, 'Speedo Fastskin Goggles','SP-005',   590000,   250000, 350),
(5, 'Wilson Pro Staff RF97',  'SP-006',  8990000,  5000000, 30);


-- ─────────────────────────────────────────────────────────────────────────────
-- 5. Customers (20 rows)
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO customers (full_name, email, city, country, segment) VALUES
('Nguyễn Văn An',    'an.nguyen@email.com',    'Hà Nội',     'Vietnam', 'vip'),
('Trần Thị Bình',    'binh.tran@email.com',    'TP HCM',     'Vietnam', 'retail'),
('Lê Minh Cường',    'cuong.le@email.com',     'Đà Nẵng',    'Vietnam', 'wholesale'),
('Phạm Thu Dung',    'dung.pham@email.com',    'Hải Phòng',  'Vietnam', 'retail'),
('Hoàng Quốc Đại',  'dai.hoang@email.com',    'Cần Thơ',    'Vietnam', 'vip'),
('Vũ Thị Lan',       'lan.vu@email.com',       'Hà Nội',     'Vietnam', 'retail'),
('Đặng Văn Minh',   'minh.dang@email.com',    'TP HCM',     'Vietnam', 'wholesale'),
('Bùi Thị Nga',      'nga.bui@email.com',      'Nha Trang',  'Vietnam', 'retail'),
('Trịnh Công Sơn',  'son.trinh@email.com',    'Huế',        'Vietnam', 'retail'),
('Đinh Thị Thanh',  'thanh.dinh@email.com',   'Đà Lạt',     'Vietnam', 'vip'),
('Ngô Văn Tú',       'tu.ngo@email.com',       'Hà Nội',     'Vietnam', 'retail'),
('Cao Thị Uyên',     'uyen.cao@email.com',     'TP HCM',     'Vietnam', 'retail'),
('Lý Văn Việt',      'viet.ly@email.com',      'Bình Dương', 'Vietnam', 'wholesale'),
('Mai Thị Xuân',     'xuan.mai@email.com',     'Long An',    'Vietnam', 'retail'),
('Phan Văn Yên',     'yen.phan@email.com',     'Đồng Nai',   'Vietnam', 'retail'),
('Tô Thị Zương',     'zuong.to@email.com',     'Hà Nội',     'Vietnam', 'vip'),
('Hồ Minh Khoa',    'khoa.ho@email.com',      'TP HCM',     'Vietnam', 'retail'),
('Lưu Thị Phương',  'phuong.luu@email.com',   'Vũng Tàu',   'Vietnam', 'retail'),
('Đoàn Văn Quân',   'quan.doan@email.com',    'Hà Nội',     'Vietnam', 'wholesale'),
('Châu Thị Ngọc',   'ngoc.chau@email.com',    'TP HCM',     'Vietnam', 'vip');


-- ─────────────────────────────────────────────────────────────────────────────
-- 6. Orders + Order Items (≈90 days of history, ~60 orders)
-- ─────────────────────────────────────────────────────────────────────────────
DO $$
DECLARE
    v_order_id INT;
BEGIN

-- Helper: insert one order with items, returns order id
-- Format: (customer_id, status, discount, created_at, items[])

-- January orders
INSERT INTO orders (customer_id, status, total_amount, discount, created_at) VALUES (1,'completed',29990000,0,'2025-01-03 09:15:00+07') RETURNING id INTO v_order_id;
INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES (v_order_id,1,1,29990000);

INSERT INTO orders (customer_id, status, total_amount, discount, created_at) VALUES (2,'completed',4780000,0,'2025-01-05 14:30:00+07') RETURNING id INTO v_order_id;
INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES (v_order_id,10,3,590000),(v_order_id,19,3,189000);

INSERT INTO orders (customer_id, status, total_amount, discount, created_at) VALUES (3,'completed',22990000,500000,'2025-01-08 10:00:00+07') RETURNING id INTO v_order_id;
INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES (v_order_id,2,1,22990000);

INSERT INTO orders (customer_id, status, total_amount, discount, created_at) VALUES (4,'cancelled',3490000,0,'2025-01-10 16:45:00+07') RETURNING id INTO v_order_id;
INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES (v_order_id,13,1,3490000);

INSERT INTO orders (customer_id, status, total_amount, discount, created_at) VALUES (5,'completed',45480000,1000000,'2025-01-12 11:20:00+07') RETURNING id INTO v_order_id;
INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES (v_order_id,3,1,35990000),(v_order_id,4,1,8990000);

INSERT INTO orders (customer_id, status, total_amount, discount, created_at) VALUES (6,'completed',2380000,0,'2025-01-15 09:00:00+07') RETURNING id INTO v_order_id;
INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES (v_order_id,20,4,229000),(v_order_id,21,4,199000),(v_order_id,22,2,249000);

INSERT INTO orders (customer_id, status, total_amount, discount, created_at) VALUES (7,'completed',39980000,0,'2025-01-18 13:30:00+07') RETURNING id INTO v_order_id;
INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES (v_order_id,5,1,16490000),(v_order_id,1,1,29990000);

INSERT INTO orders (customer_id, status, total_amount, discount, created_at) VALUES (8,'refunded',1290000,0,'2025-01-20 15:00:00+07') RETURNING id INTO v_order_id;
INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES (v_order_id,28,1,1290000);

-- February orders
INSERT INTO orders (customer_id, status, total_amount, discount, created_at) VALUES (9,'completed',8990000,0,'2025-02-02 10:30:00+07') RETURNING id INTO v_order_id;
INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES (v_order_id,4,1,8990000);

INSERT INTO orders (customer_id, status, total_amount, discount, created_at) VALUES (10,'completed',14990000,500000,'2025-02-05 14:00:00+07') RETURNING id INTO v_order_id;
INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES (v_order_id,16,1,14990000);

INSERT INTO orders (customer_id, status, total_amount, discount, created_at) VALUES (11,'completed',7180000,0,'2025-02-07 09:45:00+07') RETURNING id INTO v_order_id;
INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES (v_order_id,26,1,4290000),(v_order_id,27,1,2990000);

INSERT INTO orders (customer_id, status, total_amount, discount, created_at) VALUES (12,'completed',59780000,2000000,'2025-02-10 11:00:00+07') RETURNING id INTO v_order_id;
INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES (v_order_id,3,1,35990000),(v_order_id,25,1,12990000),(v_order_id,4,1,8990000);

INSERT INTO orders (customer_id, status, total_amount, discount, created_at) VALUES (13,'completed',5580000,0,'2025-02-13 16:15:00+07') RETURNING id INTO v_order_id;
INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES (v_order_id,8,1,3990000),(v_order_id,7,1,1290000);

INSERT INTO orders (customer_id, status, total_amount, discount, created_at) VALUES (14,'completed',2490000,0,'2025-02-15 12:30:00+07') RETURNING id INTO v_order_id;
INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES (v_order_id,11,1,2490000);

INSERT INTO orders (customer_id, status, total_amount, discount, created_at) VALUES (15,'completed',12990000,0,'2025-02-18 10:00:00+07') RETURNING id INTO v_order_id;
INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES (v_order_id,25,1,12990000);

INSERT INTO orders (customer_id, status, total_amount, discount, created_at) VALUES (1,'completed',4290000,0,'2025-02-20 14:45:00+07') RETURNING id INTO v_order_id;
INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES (v_order_id,15,1,4290000);

INSERT INTO orders (customer_id, status, total_amount, discount, created_at) VALUES (16,'completed',35990000,1000000,'2025-02-22 09:30:00+07') RETURNING id INTO v_order_id;
INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES (v_order_id,3,1,35990000);

INSERT INTO orders (customer_id, status, total_amount, discount, created_at) VALUES (17,'cancelled',7990000,0,'2025-02-25 13:00:00+07') RETURNING id INTO v_order_id;
INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES (v_order_id,18,1,7990000);

-- March orders
INSERT INTO orders (customer_id, status, total_amount, discount, created_at) VALUES (18,'completed',22990000,0,'2025-03-01 10:15:00+07') RETURNING id INTO v_order_id;
INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES (v_order_id,2,1,22990000);

INSERT INTO orders (customer_id, status, total_amount, discount, created_at) VALUES (19,'completed',9480000,0,'2025-03-03 15:30:00+07') RETURNING id INTO v_order_id;
INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES (v_order_id,4,1,8990000),(v_order_id,23,1,359000),(v_order_id,19,1,189000);

INSERT INTO orders (customer_id, status, total_amount, discount, created_at) VALUES (20,'completed',29990000,0,'2025-03-05 11:00:00+07') RETURNING id INTO v_order_id;
INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES (v_order_id,1,1,29990000);

INSERT INTO orders (customer_id, status, total_amount, discount, created_at) VALUES (5,'completed',3490000,0,'2025-03-07 09:00:00+07') RETURNING id INTO v_order_id;
INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES (v_order_id,13,1,3490000);

INSERT INTO orders (customer_id, status, total_amount, discount, created_at) VALUES (2,'completed',16490000,500000,'2025-03-10 14:00:00+07') RETURNING id INTO v_order_id;
INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES (v_order_id,5,1,16490000);

INSERT INTO orders (customer_id, status, total_amount, discount, created_at) VALUES (10,'completed',52480000,2000000,'2025-03-12 10:30:00+07') RETURNING id INTO v_order_id;
INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES (v_order_id,3,1,35990000),(v_order_id,25,1,12990000),(v_order_id,26,1,4290000);

INSERT INTO orders (customer_id, status, total_amount, discount, created_at) VALUES (3,'completed',2490000,0,'2025-03-14 16:00:00+07') RETURNING id INTO v_order_id;
INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES (v_order_id,6,1,2490000);

INSERT INTO orders (customer_id, status, total_amount, discount, created_at) VALUES (11,'completed',1770000,0,'2025-03-17 09:45:00+07') RETURNING id INTO v_order_id;
INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES (v_order_id,19,3,189000),(v_order_id,20,3,229000),(v_order_id,21,2,199000);

INSERT INTO orders (customer_id, status, total_amount, discount, created_at) VALUES (7,'completed',7990000,0,'2025-03-19 13:00:00+07') RETURNING id INTO v_order_id;
INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES (v_order_id,18,1,7990000);

INSERT INTO orders (customer_id, status, total_amount, discount, created_at) VALUES (15,'completed',8990000,0,'2025-03-21 11:30:00+07') RETURNING id INTO v_order_id;
INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES (v_order_id,30,1,8990000);

INSERT INTO orders (customer_id, status, total_amount, discount, created_at) VALUES (8,'completed',4290000,0,'2025-03-24 14:15:00+07') RETURNING id INTO v_order_id;
INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES (v_order_id,15,1,4290000);

INSERT INTO orders (customer_id, status, total_amount, discount, created_at) VALUES (13,'completed',3980000,0,'2025-03-26 10:00:00+07') RETURNING id INTO v_order_id;
INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES (v_order_id,9,1,1890000),(v_order_id,12,3,690000);

INSERT INTO orders (customer_id, status, total_amount, discount, created_at) VALUES (16,'completed',14990000,0,'2025-03-28 15:45:00+07') RETURNING id INTO v_order_id;
INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES (v_order_id,16,1,14990000);

END $$;


-- ─────────────────────────────────────────────────────────────────────────────
-- 7. Populate daily_sales (derived from orders)
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO daily_sales (date, total_orders, total_revenue, total_cost, avg_order_value)
SELECT
    DATE(o.created_at AT TIME ZONE 'Asia/Ho_Chi_Minh')                         AS date,
    COUNT(DISTINCT o.id)                                                         AS total_orders,
    SUM(o.total_amount)                                                          AS total_revenue,
    SUM(oi.quantity * p.cost)                                                    AS total_cost,
    AVG(o.total_amount)                                                          AS avg_order_value
FROM orders o
JOIN order_items oi ON oi.order_id = o.id
JOIN products   p   ON p.id = oi.product_id
WHERE o.status NOT IN ('cancelled', 'refunded')
GROUP BY 1
ON CONFLICT (date) DO UPDATE SET
    total_orders    = EXCLUDED.total_orders,
    total_revenue   = EXCLUDED.total_revenue,
    total_cost      = EXCLUDED.total_cost,
    avg_order_value = EXCLUDED.avg_order_value;


-- ─────────────────────────────────────────────────────────────────────────────
-- 8. Quick verification
-- ─────────────────────────────────────────────────────────────────────────────
SELECT 'categories'  AS tbl, COUNT(*) FROM categories
UNION ALL SELECT 'products',  COUNT(*) FROM products
UNION ALL SELECT 'customers', COUNT(*) FROM customers
UNION ALL SELECT 'orders',    COUNT(*) FROM orders
UNION ALL SELECT 'order_items',COUNT(*) FROM order_items
UNION ALL SELECT 'daily_sales',COUNT(*) FROM daily_sales;