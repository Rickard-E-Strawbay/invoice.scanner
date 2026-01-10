-- Invoice Scanner Database Initialization

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    company_id UUID NOT NULL,
    terms_accepted BOOLEAN DEFAULT FALSE,
    terms_version VARCHAR(10),
    weekly_summary BOOLEAN DEFAULT FALSE,
    receive_notifications BOOLEAN DEFAULT FALSE,
    marketing_opt_in BOOLEAN DEFAULT FALSE,
    user_enabled BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP,
    role_key INT DEFAULT 10,
    reset_token VARCHAR(255),
    reset_token_expires TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    role_key INT,
    role_name VARCHAR(255) UNIQUE NOT NULL,
    role_description TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);




CREATE TABLE IF NOT EXISTS users_company (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_email VARCHAR(255) NOT NULL,
    company_name VARCHAR(255) NOT NULL, 
    organization_id VARCHAR(100) NOT NULL,  
    price_plan_key INT DEFAULT 10,
    company_enabled BOOLEAN DEFAULT FALSE,
    company_settings JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users_company_billing (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES users_company(id) ON DELETE CASCADE,
    billing_contact_name VARCHAR(255),
    billing_contact_email VARCHAR(255),
    country VARCHAR(100),
    city VARCHAR(100),
    postal_code VARCHAR(20),
    street_address TEXT,
    vat_number VARCHAR(50),
    payment_method VARCHAR(100),
    last_payment_date TIMESTAMP,
    next_billing_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_logs(
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    action VARCHAR(255) NOT NULL,
    details JSONB
);

CREATE TABLE IF NOT EXISTS price_plans(
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    price_plan_key INT UNIQUE NOT NULL,
    plan_name VARCHAR(100) NOT NULL,
    plan_description TEXT,
    price_per_month DECIMAL(10, 2) NOT NULL,
    features JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documents(
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES users_company(id),
    uploaded_by UUID REFERENCES users(id),
    raw_format VARCHAR(50),
    raw_filename VARCHAR(255),
    document_name VARCHAR(255),
    processed_image_filename VARCHAR(255),
    content_type VARCHAR(100),
    status VARCHAR(50) DEFAULT 'uploaded',
    error_message TEXT,
    predicted_accuracy DECIMAL(5, 2),
    is_training BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, document_name)
);

CREATE TABLE IF NOT EXISTS document_status(
    id SERIAL PRIMARY KEY,
    sequence INT UNIQUE NOT NULL,
    status_key VARCHAR(50) UNIQUE NOT NULL,
    status_name VARCHAR(100) NOT NULL,
    status_description TEXT
);

INSERT INTO document_status (sequence, status_key, status_name, status_description) VALUES
(0, 'uploaded', 'Uploaded', 'Document has been uploaded and is pending processing'),
(10, 'preprocessing', 'Preprocessing', 'Document is currently being preprocessed'),
(20, 'preprocess_error', 'Preprocess Error', 'Error occurred during document preprocessing'),
(30, 'preprocessed', 'Preprocessed', 'Document has been successfully preprocessed'),
(40, 'ocr_extracting', 'Ocr Extracting', 'OCR extraction is in progress'),
(45, 'ocr_error', 'Ocr Error', 'Error occurred during OCR extraction'),
(50, 'predicting', 'Predicting', 'Document data prediction is in progress'),
(60, 'predict_error', 'Predict Error', 'Error occurred during document data prediction'),
(70, 'predicted', 'Predicted', 'Document data has been successfully predicted'),
(80, 'extraction', 'Extraction', 'Document attribute extraction is in progress'),
(90, 'extraction_error', 'Extraction Error', 'Error occurred during document attribute extraction'),
(100, 'statistics_processing', 'Statistics Processing', 'Document statistics processing is in progress'),
(110, 'statistics_processing_error', 'Statistics Processing Error', 'Error occurred during document statistics processing'),
(115, 'automated_evaluation', 'Automated Evaluation', 'Document is undergoing automated evaluation'),
(120, 'automated_evaluation_error', 'Automated Evaluation Error', 'Error occurred during automated evaluation'),
(125, 'manual_review', 'Manual Review', 'Document requires manual review'),
(127, 'manual_review_error', 'Manual Review Error', 'Error occurred during manual review'),
(130, 'approved', 'Approved', 'Document is approved for export'),
(140, 'exporting', 'Exporting', 'Document is being exported'),
(150, 'export_error', 'Export Error', 'Error occurred during document export'),
(160, 'exported', 'Exported', 'Document has been successfully exported'),
(170, 'training_data', 'Training', 'Document is selected as training data'),
(180, 'error', 'Error', 'An unknown error occurred during document processing');

INSERT INTO price_plans
(price_plan_key, plan_name, plan_description, price_per_month, features) VALUES
( 1000,'Admin', 'Unlimited', 0, '{}'),
( 40,'Enterprise', 'Up to 20k invoices per month (€13c/invoice)', 1400, '{"api_access": true, "ftp_integration": true, "auto_export": true,"email_scan": false, "batch_scanning": true, "batch_download": true}'),
( 30,'Large', 'Up to 5k invoices per month (€18c/invoice)', 909, '{"api_access": true, "ftp_integration": true, "auto_export": true,"email_scan": false, "batch_scanning": true, "batch_download": true}'),
( 20,'Medium', 'Up to 1k invoices per month (€28c/invoice)', 272, '{"api_access": false, "ftp_integration": true, "auto_export": false,"email_scan": false, "batch_scanning": true, "batch_download": true}'),
( 15,'Basic', 'Up to 100 invoices per month (€36c/invoice)', 36, '{"api_access": false, "ftp_integration": false, "auto_export": false,"email_scan": false, "batch_scanning": false, "batch_download": false}'),
( 10,'Starter', 'Up to 10 invoices per month', 0, '{}');

INSERT INTO user_roles (role_name, role_key, role_description) VALUES
('Strawbay Admin', 1000, 'System Admin with access to approve new Companies'),
('Company Admin', 50, 'Company Admin with full access to company data, and approve Company Users'),
('Company User', 10, 'Able to Scan, View and Manage Invoices for the Company')
ON CONFLICT (role_name) DO NOTHING;

-- Insert sample companies for testing
INSERT INTO users_company (company_email, company_name, organization_id, company_enabled, price_plan_key) VALUES
('info@strawbay.se', 'Strawbay AB', '559421-9601', TRUE, 1000),
('info@test.se', 'Acme AB', '123456-7890', TRUE, 10);

-- Insert sample users
INSERT INTO users (email, password_hash, name, role_key, company_id, terms_accepted, user_enabled, terms_version) 
SELECT 
    'rickard@strawbay.io', 
    'scrypt:32768:8:1$volUxXkGjGMmZaHy$ef9cfe94c1a1d84dbce69dfa5839570d23827daf5e46b67ffc81bf07ca5aca4da82f03144755b47fa73cff99d8b8cadcb6315a58bdc7d98026d123c2fd12d139',
    'Rickard Elmqvist', 
    1000,
    id,
    TRUE,
    TRUE,
    '1.0'
FROM users_company 
WHERE organization_id = '559421-9601';

INSERT INTO users (email, password_hash, name, role_key, company_id, terms_accepted, user_enabled, terms_version) 
SELECT 
    'andy@strawbay.io', 
    'scrypt:32768:8:1$volUxXkGjGMmZaHy$ef9cfe94c1a1d84dbce69dfa5839570d23827daf5e46b67ffc81bf07ca5aca4da82f03144755b47fa73cff99d8b8cadcb6315a58bdc7d98026d123c2fd12d139',
    'Andrii Khyzhniak', 
    1000,
    id,
    TRUE,
    TRUE,
    '1.0'
FROM users_company 
WHERE organization_id = '559421-9601';

INSERT INTO users (email, password_hash, name, role_key, company_id, terms_accepted, user_enabled, terms_version) 
SELECT 
    'claes@strawbay.io', 
    'scrypt:32768:8:1$volUxXkGjGMmZaHy$ef9cfe94c1a1d84dbce69dfa5839570d23827daf5e46b67ffc81bf07ca5aca4da82f03144755b47fa73cff99d8b8cadcb6315a58bdc7d98026d123c2fd12d139',
    'Claes Ramel', 
    1000,
    id,
    TRUE,
    TRUE,
    '1.0'
FROM users_company 
WHERE organization_id = '559421-9601';

-- Insert test user as Company Admin
INSERT INTO users (email, password_hash, name, role_key, company_id, terms_accepted, user_enabled, terms_version) 
SELECT 
    'test-admin@test.se', 
    'scrypt:32768:8:1$volUxXkGjGMmZaHy$ef9cfe94c1a1d84dbce69dfa5839570d23827daf5e46b67ffc81bf07ca5aca4da82f03144755b47fa73cff99d8b8cadcb6315a58bdc7d98026d123c2fd12d139',
    'Test Company Admin', 
    50,
    id,
    TRUE,
    TRUE,
    '1.0'
FROM users_company 
WHERE organization_id = '123456-7890';

-- Insert test user as Company Admin
INSERT INTO users (email, password_hash, name, role_key, company_id, terms_accepted, user_enabled, terms_version) 
SELECT 
    'test-user@test.se', 
    'scrypt:32768:8:1$volUxXkGjGMmZaHy$ef9cfe94c1a1d84dbce69dfa5839570d23827daf5e46b67ffc81bf07ca5aca4da82f03144755b47fa73cff99d8b8cadcb6315a58bdc7d98026d123c2fd12d139',
    'Test Company User', 
    10,
    id,
    TRUE,
    TRUE,
    '1.0'
FROM users_company 
WHERE organization_id = '123456-7890';


