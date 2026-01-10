# Smart Café Management System

## Project Overview

The **Smart Café Management System** is a web-based application built using **Flask** and **MySQL** that automates café operations such as table booking, order management, ingredient stock tracking, and payment handling.

It is designed mainly for **customer-side ordering interfaces**, with support for real-time inventory deduction and future admin/manager extensions.

### The system ensures:
- Real-time ingredient stock validation
- Prevention of over-ordering
- Efficient table utilization
- Smooth order lifecycle management from creation to payment and receipt


## Key Features

### 1. Order Management
- Create a new order by selecting a table number
- Add multiple menu items with quantities
- Add more items to an existing active order before payment
- View order summary before payment
- Finalize orders after completion

### 2. Menu & Ingredients
- Menu items are linked with required ingredients
- Automatic ingredient stock deduction after ordering
- Orders are blocked if ingredients are insufficient

### 3. Table Management
- Tables are automatically:
  - **Booked** when an order is created
  - **Freed** when the order is completed
- Prevents multiple active orders on the same table

### 4. Payment Handling
- Supports **Cash** and **Card** payment methods
- Payment status tracking (`pending`, `paid`)
- Payment page and receipt generation
- Receipt is only available after successful payment

### 5. Analytics
- Displays **Top 3 selling products** based on completed orders
- Sales data calculated for the **last 30 days**



## Requirements

- **Programming Language:** Python  
- **Framework:** Flask  
- **Database:** MySQL  
- **Frontend:** HTML, CSS (Bootstrap)  
- **Operating System:** Windows / Linux  

