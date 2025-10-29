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