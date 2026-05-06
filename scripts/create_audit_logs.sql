CREATE TABLE IF NOT EXISTS audit_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NULL,
    action VARCHAR(255) NOT NULL,
    resource_type VARCHAR(100) NULL,
    resource_id INT NULL,
    ip_address VARCHAR(100) NULL,
    user_agent TEXT NULL,
    details TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
