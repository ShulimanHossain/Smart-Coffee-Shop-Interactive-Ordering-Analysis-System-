CREATE DATABASE Cafe;
USE cafe;

CREATE TABLE ingredients(
    ing_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    quantity DECIMAL(10,2) NOT NULL,
    unit VARCHAR(20) NOT NULL
);

CREATE TABLE  menu (
    item_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL
);

CREATE TABLE  item_ingredients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    item_id INT NOT NULL,
    ing_id INT NOT NULL,
    quantity_needed DECIMAL(10,2) NOT NULL, 
    FOREIGN KEY (item_id) REFERENCES menu(item_id) ON DELETE CASCADE,
    FOREIGN KEY (ing_id) REFERENCES ingredients(ing_id) ON DELETE CASCADE
);

CREATE TABLE cafe_tables(
    table_no INT PRIMARY KEY,
    status ENUM('Booked','Free') DEFAULT 'Free'
);
SELECT * FROM Orders;

CREATE TABLE Orders(
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    table_no INT NOT NULL,
    total_bill DECIMAL(10,2) NOT NULL,
    status ENUM('active','completed','cancle') DEFAULT 'active',
    payment_method ENUM ('cash','card') DEFAULT NULL,
    payment_status ENUM('pending','paid') DEFAULT 'pending',
    order_date DATE DEFAULT (CURRENT_DATE),
    order_time TIME DEFAULT (CURRENT_TIME),
    FOREIGN KEY (table_no) REFERENCES cafe_tables(table_no)
);

CREATE TABLE Order_details(
    order_details_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    item_id INT NOT NULL,
    quantity INT NOT NULL,
    FOREIGN KEY (order_id) REFERENCES Orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES Menu(item_id) ON DELETE CASCADE
);
INSERT INTO ingredients (name, quantity, unit) VALUES
('Coffee Beans', 1000, 'g'),
('Milk', 5000, 'ml'),
('Chocolate Syrup', 1000, 'ml'),
('Tea Leaves', 500, 'g'),
('Sugar', 2000, 'g');

INSERT INTO menu (name, price) VALUES
('Espresso', 2.50),
('Latte', 3.50),
('Cappuccino', 3.00),
('Mocha', 4.00),
('Tea', 1.50);


INSERT INTO item_ingredients (item_id, ing_id, quantity_needed) VALUES
(1, 1, 10),        -- Espresso -> Coffee Beans 10g
(2, 1, 10),        -- Latte -> Coffee Beans 10g
(2, 2, 200),       -- Latte -> Milk 200ml
(3, 1, 10),        -- Cappuccino -> Coffee Beans 10g
(3, 2, 150),       -- Cappuccino -> Milk 150ml
(4, 1, 10),        -- Mocha -> Coffee Beans 10g
(4, 2, 150),       -- Mocha -> Milk 150ml
(4, 3, 50),        -- Mocha -> Chocolate Syrup 50ml
(5, 4, 5),         -- Tea -> Tea Leaves 5g
(5, 5, 10);

INSERT INTO Order_details (order_id, item_id, quantity) VALUES
(11, 1, 2),
(11, 3, 1),
(12, 2, 1),
(13, 4, 2),
(15, 5, 3);


INSERT INTO Orders (table_no, total_bill, status) VALUES
(1, 450.00, 'completed'),
(2, 320.50, 'active'),
(3, 250.00, 'completed'),
(4, 180.75, 'cancle'),
(5, 600.00, 'active');
INSERT INTO cafe_tables (table_no, status) VALUES
(1, 'Free'),
(2, 'Booked'),
(3, 'Free'),
(4, 'Booked'),
(5, 'Free');

SHOW TABLES FROM Cafe;