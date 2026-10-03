-- ============================================================================
-- COMMUNITY PARKING SYSTEM — MySQL Database Schema
-- Final-Year CSE Capstone Project
-- ============================================================================

CREATE DATABASE IF NOT EXISTS `community_parking_db` 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE `community_parking_db`;

-- 1. USERS TABLE (Drivers, Owners, Administrators)
CREATE TABLE IF NOT EXISTS `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(100) NOT NULL,
    `email` VARCHAR(120) NOT NULL UNIQUE,
    `phone` VARCHAR(20) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `role` ENUM('DRIVER', 'OWNER', 'ADMIN') NOT NULL DEFAULT 'DRIVER',
    `status` ENUM('ACTIVE', 'SUSPENDED') NOT NULL DEFAULT 'ACTIVE',
    `owner_status` ENUM('PENDING', 'APPROVED', 'REJECTED', 'SUSPENDED') DEFAULT NULL,
    `owner_id_proof` VARCHAR(255) DEFAULT NULL,
    `owner_address` VARCHAR(255) DEFAULT NULL,
    `rejection_reason` TEXT DEFAULT NULL,
    `upi_id` VARCHAR(100) DEFAULT NULL,
    `profile_image` VARCHAR(255) DEFAULT 'default_avatar.png',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_users_role` (`role`),
    INDEX `idx_users_owner_status` (`owner_status`)
) ENGINE=InnoDB;

-- 2. PARKING SPACES TABLE (Listings by Community/Property Owners)
CREATE TABLE IF NOT EXISTS `parking_spaces` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `owner_id` INT NOT NULL,
    `title` VARCHAR(150) NOT NULL,
    `description` TEXT NOT NULL,
    `address` VARCHAR(255) NOT NULL,
    `locality` VARCHAR(100) NOT NULL,
    `city` VARCHAR(100) NOT NULL DEFAULT 'Bangalore',
    `latitude` DECIMAL(10, 8) NOT NULL,
    `longitude` DECIMAL(11, 8) NOT NULL,
    `parking_type` ENUM('Residential', 'Commercial', 'Private Driveway', 'Open Lot', 'Covered Garage', 'Community Shared') NOT NULL DEFAULT 'Private Driveway',
    `vehicle_types` VARCHAR(100) NOT NULL DEFAULT 'Car, Two Wheeler',
    `total_slots` INT NOT NULL DEFAULT 1,
    `price_per_hour` DECIMAL(8, 2) NOT NULL,
    `price_per_day` DECIMAL(8, 2) DEFAULT NULL,
    `operating_start` TIME NOT NULL DEFAULT '06:00:00',
    `operating_end` TIME NOT NULL DEFAULT '22:00:00',
    `available_days` VARCHAR(100) NOT NULL DEFAULT 'Mon,Tue,Wed,Thu,Fri,Sat,Sun',
    `rules` TEXT DEFAULT NULL,
    `amenities` VARCHAR(255) DEFAULT 'CCTV, Security, Well Lit',
    `image_url` VARCHAR(255) DEFAULT 'default_parking.jpg',
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
    `approval_status` ENUM('APPROVED', 'PENDING', 'REJECTED') NOT NULL DEFAULT 'APPROVED',
    `upi_id` VARCHAR(100) DEFAULT NULL,
    `upi_qr_image` VARCHAR(255) DEFAULT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`owner_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    INDEX `idx_parking_location` (`latitude`, `longitude`),
    INDEX `idx_parking_locality` (`locality`, `city`),
    INDEX `idx_parking_status` (`is_active`, `approval_status`)
) ENGINE=InnoDB;

-- 3. PARKING IMAGES TABLE (Multi-image Gallery)
CREATE TABLE IF NOT EXISTS `parking_images` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `parking_space_id` INT NOT NULL,
    `image_url` VARCHAR(255) NOT NULL,
    `caption` VARCHAR(100) DEFAULT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`parking_space_id`) REFERENCES `parking_spaces`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 4. BOOKINGS TABLE (Reservations & Lifecycle)
CREATE TABLE IF NOT EXISTS `bookings` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `booking_reference` VARCHAR(30) NOT NULL UNIQUE,
    `user_id` INT NOT NULL,
    `parking_space_id` INT NOT NULL,
    `booking_date` DATE NOT NULL,
    `start_time` TIME NOT NULL,
    `end_time` TIME NOT NULL,
    `duration_hours` DECIMAL(5, 2) NOT NULL,
    `vehicle_type` VARCHAR(50) NOT NULL,
    `vehicle_plate` VARCHAR(30) NOT NULL,
    `total_price` DECIMAL(10, 2) NOT NULL,
    `status` ENUM('PENDING', 'APPROVED', 'ACTIVE', 'COMPLETED', 'CANCELLED', 'REJECTED') NOT NULL DEFAULT 'PENDING',
    `qr_token` VARCHAR(100) NOT NULL UNIQUE,
    `check_in_time` DATETIME DEFAULT NULL,
    `check_out_time` DATETIME DEFAULT NULL,
    `cancellation_reason` TEXT DEFAULT NULL,
    `is_emergency` BOOLEAN NOT NULL DEFAULT FALSE,
    `payment_status` ENUM('PAID', 'PENDING', 'REFUNDED') NOT NULL DEFAULT 'PAID',
    `payment_method` VARCHAR(50) NOT NULL DEFAULT 'UPI / Online',
    `payment_transaction_id` VARCHAR(100) DEFAULT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`parking_space_id`) REFERENCES `parking_spaces`(`id`) ON DELETE CASCADE,
    INDEX `idx_booking_date_time` (`booking_date`, `start_time`, `end_time`),
    INDEX `idx_booking_status` (`status`),
    INDEX `idx_booking_payment` (`payment_status`, `payment_transaction_id`),
    INDEX `idx_booking_qr` (`qr_token`)
) ENGINE=InnoDB;

-- 5. REVIEWS & RATINGS TABLE
CREATE TABLE IF NOT EXISTS `reviews` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `booking_id` INT NOT NULL UNIQUE,
    `parking_space_id` INT NOT NULL,
    `user_id` INT NOT NULL,
    `rating` TINYINT NOT NULL CHECK (`rating` BETWEEN 1 AND 5),
    `comment` TEXT NOT NULL,
    `is_moderated` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`booking_id`) REFERENCES `bookings`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`parking_space_id`) REFERENCES `parking_spaces`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    INDEX `idx_reviews_parking` (`parking_space_id`)
) ENGINE=InnoDB;

-- 6. NOTIFICATIONS TABLE (User / Owner / Admin alerts)
CREATE TABLE IF NOT EXISTS `notifications` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `title` VARCHAR(150) NOT NULL,
    `message` TEXT NOT NULL,
    `link` VARCHAR(255) DEFAULT NULL,
    `is_read` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    INDEX `idx_notifs_user` (`user_id`, `is_read`)
) ENGINE=InnoDB;

-- 7. AUDIT LOGS TABLE (System Actions & Traceability)
CREATE TABLE IF NOT EXISTS `audit_logs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `actor_id` INT DEFAULT NULL,
    `action` VARCHAR(100) NOT NULL,
    `target_entity` VARCHAR(50) NOT NULL,
    `target_id` INT DEFAULT NULL,
    `details` TEXT DEFAULT NULL,
    `ip_address` VARCHAR(45) DEFAULT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`actor_id`) REFERENCES `users`(`id`) ON DELETE SET NULL,
    INDEX `idx_audit_action` (`action`),
    INDEX `idx_audit_created` (`created_at`)
) ENGINE=InnoDB;
