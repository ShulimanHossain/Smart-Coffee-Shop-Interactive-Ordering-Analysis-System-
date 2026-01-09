CREATE DATABASE Cafe_ML;
USE Cafe_ML;

CREATE TABLE User(
     id INT AUTO_INCREMENT PRIMARY KEY,
     user_code VARCHAR(20) UNIQUE,
     name VARCHAR(20) NOT NULL,
     email VARCHAR(20) UNIQUE NOT NULL,
     password VARCHAR(20) NOT NULL,
     role ENUM('admin','manager','staff') NOT NULL ,
     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Ingredients(
    ing_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    quantity DECIMAL(10,2) NOT NULL,
    unit VARCHAR(20) NOT NULL
);

CREATE TABLE  Menu (
    item_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL
);

CREATE TABLE  Item_ingredients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    item_id INT NOT NULL,
    ing_id INT NOT NULL,
    quantity_needed DECIMAL(10,2) NOT NULL, 
    FOREIGN KEY (item_id) REFERENCES menu(item_id) ON DELETE CASCADE,
    FOREIGN KEY (ing_id) REFERENCES ingredients(ing_id) ON DELETE CASCADE
);

CREATE TABLE Cafe_tables(
    table_no INT PRIMARY KEY,
    status ENUM('Booked','Free') DEFAULT 'Free'
);
SELECT * FROM Orders;

CREATE TABLE Orders(
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    table_no INT NOT NULL,
    total_bill DECIMAL(10,2) NOT NULL,
    status ENUM('active','completed','cancel') DEFAULT 'active',
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
