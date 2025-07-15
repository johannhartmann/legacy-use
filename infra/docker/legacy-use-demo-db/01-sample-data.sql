-- PostgreSQL initialization script for Legacy Use
-- This script runs ONLY when the database is first created (empty pgdata volume)
-- It will NOT run if the database already contains data

-- Enable UUID extension for PostgreSQL
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create alembic_version table for migration tracking
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Create targets table
CREATE TABLE IF NOT EXISTS targets (
    id TEXT NOT NULL,
    name VARCHAR NOT NULL,
    type VARCHAR NOT NULL,
    host VARCHAR NOT NULL,
    port VARCHAR,
    username VARCHAR,
    password VARCHAR NOT NULL,
    vpn_config VARCHAR,
    vpn_username VARCHAR,
    vpn_password VARCHAR,
    width VARCHAR NOT NULL DEFAULT '1024',
    height VARCHAR NOT NULL DEFAULT '768',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    is_archived BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (id)
);

-- Create sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT NOT NULL,
    name VARCHAR NOT NULL,
    description VARCHAR,
    target_id TEXT NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'created',
    state VARCHAR NOT NULL DEFAULT 'initializing',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    is_archived BOOLEAN DEFAULT FALSE,
    archive_reason VARCHAR,
    last_job_time TIMESTAMP,
    container_id VARCHAR,
    container_ip VARCHAR,
    PRIMARY KEY (id),
    FOREIGN KEY (target_id) REFERENCES targets(id)
);

-- Create api_definitions table
CREATE TABLE IF NOT EXISTS api_definitions (
    id TEXT NOT NULL,
    name VARCHAR NOT NULL,
    description VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_archived BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (id),
    UNIQUE (name)
);

-- Create api_definition_versions table
CREATE TABLE IF NOT EXISTS api_definition_versions (
    id TEXT NOT NULL,
    api_definition_id TEXT NOT NULL,
    version_number VARCHAR NOT NULL,
    parameters JSONB NOT NULL DEFAULT '[]',
    prompt VARCHAR NOT NULL,
    prompt_cleanup VARCHAR NOT NULL,
    response_example JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (id),
    FOREIGN KEY (api_definition_id) REFERENCES api_definitions(id)
);

-- Create jobs table
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    session_id TEXT,
    api_name VARCHAR,
    api_definition_version_id TEXT,
    parameters JSONB,
    status VARCHAR DEFAULT 'pending',
    result JSONB,
    error VARCHAR,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    total_input_tokens INTEGER,
    total_output_tokens INTEGER,
    PRIMARY KEY (id),
    FOREIGN KEY (target_id) REFERENCES targets(id),
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (api_definition_version_id) REFERENCES api_definition_versions(id)
);

-- Create job_logs table
CREATE TABLE IF NOT EXISTS job_logs (
    id TEXT NOT NULL,
    job_id TEXT,
    timestamp TIMESTAMP DEFAULT NOW(),
    log_type VARCHAR,
    content JSONB,
    content_trimmed JSONB,
    PRIMARY KEY (id),
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);

-- Create job_messages table
CREATE TABLE IF NOT EXISTS job_messages (
    id TEXT NOT NULL,
    job_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    role VARCHAR NOT NULL,
    message_content JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (id),
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
);

-- Create indexes
CREATE INDEX IF NOT EXISTS ix_job_messages_job_id ON job_messages (job_id);
CREATE INDEX IF NOT EXISTS ix_jobmessage_job_id_sequence ON job_messages (job_id, sequence);

-- Insert current migration version
INSERT INTO alembic_version (version_num) VALUES ('3814b7855961') 
ON CONFLICT (version_num) DO NOTHING;

-- Sample Targets
INSERT INTO targets (
    id, 
    name, 
    type, 
    host, 
    port, 
    username, 
    password, 
    width, 
    height, 
    created_at, 
    updated_at, 
    is_archived,
    vpn_config,
    vpn_username,
    vpn_password
) VALUES 
(
    '360553ec-2ad2-4dfa-90b5-b6d49b1e7bf3',
    'Linux Desktop (GnuCash)',
    'vnc',
    'linux-machine',
    '5900',
    '',
    'password123',
    '1920',
    '1080',
    NOW(),
    NOW(),
    false,
    '',
    '',
    ''
),
(
    'f47ac10b-58cc-4372-a567-0e02b2c3d479',
    'Wine (Windows Apps)',
    'vnc',
    'wine-target',
    '5900',
    '',
    'wine',
    '1920',
    '1080',
    NOW(),
    NOW(),
    false,
    '',
    '',
    ''
),
(
    'a8c3d5e2-7b61-4f89-92a4-1e5c8d9f3b27',
    'Android Emulator',
    'vnc',
    'android-target',
    '5900',
    '',
    '',
    '1080',
    '2340',
    NOW(),
    NOW(),
    false,
    '',
    '',
    ''
)
ON CONFLICT (id) DO NOTHING;

-- Sample API Definitions
INSERT INTO api_definitions (
    id,
    name,
    description,
    created_at,
    updated_at,
    is_archived
) VALUES 
(
    'de28fb1e-3d79-4357-8db7-4c438b579d95',
    'GnuCash - Read Account Information',
    'API to get account information',
    NOW(),
    NOW(),
    false
),
(
    '547ca289-9543-49b2-866b-36e5235f1b0c',
    'GnuCash - Add new invoice',
    'Write new information into GnuCash',
    NOW(),
    NOW(),
    false
)
ON CONFLICT (id) DO NOTHING;

-- Sample API Definition Versions (only active versions)
INSERT INTO api_definition_versions (
    id,
    api_definition_id,
    version_number,
    parameters,
    prompt,
    prompt_cleanup,
    response_example,
    created_at,
    is_active
) VALUES 
(
    'b6541819-4853-4bb5-ad42-8bb45067055a',
    'de28fb1e-3d79-4357-8db7-4c438b579d95',
    '5',
    '[]',
    'You are acting as an accountant working with GnuCash to extract specific transaction data. Please follow the steps below:

1. In the account overview, locate the **Income** account and click the triangle to its left to expand the subaccounts.

2. From the expanded list, double-click on the subaccount labeled **"Consulting"** to open its transaction view.

3. In the transaction list, locate the entries associated with **CUSTOMER C**.

4. For each transaction related to CUSTOMER C, extract the following information:

   * **Income** (amount)
   * **Date** of the transaction
   * **R** status (reconciliation status)

5. Return the extracted data as a JSON array, where each entry contains `date`, `income`, and `reconciliation_status`.

### Note on the "R" Column:

The "R" column indicates the reconciliation status of a transaction:

* `"n"` = Not reconciled
* `"c"` = Cleared
* `"y"` or `"R"` = Reconciled

### Notes on Popups

* If you see the popup **"GnuCash cannot obtain the lock"**, always click **"Open Anyway"**.
* If you see the popup **"Tip of the Day"**, simply close it.
* If both popups appear, **always handle the "GnuCash cannot obtain the lock" popup first**!
',
    'Close the **"Consulting"** tab.',
    '{"date": "2025-05-15", "income": 1200, "reconciliation_status": "y"}',
    NOW(),
    true
),
(
    'c3c22f1c-24a6-4655-b1b2-e94f6ae11692',
    '547ca289-9543-49b2-866b-36e5235f1b0c',
    '5',
    '[{"name": "num", "description": "The id of the invoice", "type": "string", "required": false, "default": "NV-010"}, {"name": "description", "description": "Additional information about the invoice", "type": "string", "required": false, "default": "PAID - Customer X"}, {"name": "deposit", "description": "The amount of the transaction to add.", "type": "string", "required": false, "default": "280"}]',
    'You are acting as an accountant working with GnuCash to add a new transaction. Please follow the steps below:

1. In the account overview, locate the **Income** account. Click the triangle to its left to expand its subaccounts.

2. From the expanded list, double-click on the **"Consulting"** subaccount to open its transaction view.

3. Scroll to the bottom of the transaction list and locate the last empty row.

4. In this empty row, enter the following details:

   * **num:** {{num}}
   * **description:** {{description}}
   * **deposit:** {{deposit}}

5. Press **Enter** to save the transaction.

### Notes on Input Data

* If no input data is given, use these as fallback: {''num'': ''NV-010'', ''description'': ''PAID - Customer X'', ''deposit'': ''280''}
* Make sure to be in the actual "Deposit"-column and not in the "Withdraw"-column.

### Notes on Popups

* If you see the popup **"GnuCash cannot obtain the lock"**, always click **"Open Anyway"**.
* If you see the popup **"Tip of the Day"**, simply close it.
* If both popups appear, **always handle the "GnuCash cannot obtain the lock" popup first**!
',
    'Close the **"Consulting"** subaccount tab.',
    '{"success": true}',
    NOW(),
    true
)
ON CONFLICT (id) DO NOTHING;

-- Log successful initialization
DO $$ 
BEGIN 
    RAISE NOTICE 'Legacy Use database initialized with sample data successfully!';
    RAISE NOTICE 'Created % targets and % API definitions', 
        (SELECT COUNT(*) FROM targets WHERE is_archived = false),
        (SELECT COUNT(*) FROM api_definitions);
END $$; 