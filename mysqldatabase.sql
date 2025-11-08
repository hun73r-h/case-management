-- 🔁 Create database
CREATE DATABASE IF NOT EXISTS case_management;
USE case_management;

-- ⚠ Drop old tables (only if resetting)
DROP TABLE IF EXISTS cases;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS admins;

-- 📦 Create `cases` table
CREATE TABLE cases (
    id INT AUTO_INCREMENT PRIMARY KEY,
    case_no VARCHAR(50),
    po_no VARCHAR(100),
    r_note_no VARCHAR(100),
    subject VARCHAR(255),
    co6_date DATE,
    name VARCHAR(100),
    sent_to VARCHAR(100),
    sent_date DATE,
    no_of_days_with_accounts VARCHAR(50),
    no_of_days_with_stores VARCHAR(50),
    received BOOLEAN DEFAULT FALSE,
    received_date DATETIME,
    default_date DATE
);

-- 👤 Create `users` table
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    email VARCHAR(100),
    phone VARCHAR(20)
);

-- 🛡️ Create `admins` table
CREATE TABLE admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    email VARCHAR(100),
    phone VARCHAR(20)
);
