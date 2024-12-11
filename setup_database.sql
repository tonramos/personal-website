-- Create database if not exists
CREATE DATABASE IF NOT EXISTS users_db;
USE users_db;

-- Create users_info table
CREATE TABLE IF NOT EXISTS users_info (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(100) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    birthday DATE,
    contact_number VARCHAR(20),
    age INT,
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
); 