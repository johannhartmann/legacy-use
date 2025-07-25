"""add_sample_targets_data

Revision ID: 450b1b184d8a
Revises: 1fe76136b57e
Create Date: 2025-07-20 16:47:46.541467

"""
import os
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '450b1b184d8a'
down_revision: Union[str, None] = '1fe76136b57e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Insert sample targets
    op.execute("""
            INSERT INTO targets (
                id, name, type, host, port, username, password, 
                width, height, vnc_path, novnc_port, created_at, updated_at, 
                is_archived, vpn_config, vpn_username, vpn_password, pool_type
            ) VALUES 
            (
                '360553ec-2ad2-4dfa-90b5-b6d49b1e7bf3',
                'Linux Desktop (GnuCash)',
                'vnc',
                'legacy-use-linux-target',  -- Use Kubernetes service name
                '5900',
                '',
                '',
                '1920',
                '1080',
                'static/vnc.html',
                '80',  -- Linux target uses nginx on port 80
                NOW(),
                NOW(),
                false,
                '',
                '',
                '',
                'linux'
            ),
            (
                'f47ac10b-58cc-4372-a567-0e02b2c3d479',
                'Wine (Windows Apps)',
                'vnc',
                'legacy-use-wine-target',  -- Use Kubernetes service name
                '5900',
                '',
                '',  -- No password
                '1920',
                '1080',
                'vnc.html',
                '6080',  -- Standard noVNC port
                NOW(),
                NOW(),
                false,
                '',
                '',
                '',
                'wine'
            ),
            (
                'a8c3d5e2-7b61-4f89-92a4-1e5c8d9f3b27',
                'Android Emulator',
                'vnc',
                'legacy-use-android-target',  -- Use Kubernetes service name
                '5900',
                '',
                '',
                '1080',
                '2340',
                'vnc.html',
                '6080',  -- Standard noVNC port
                NOW(),
                NOW(),
                false,
                '',
                '',
                '',
                'android'
            ),
            (
                'b5d2f4a8-9c31-4e72-a893-2f6d9e8c4a35',
                'Windows XP VM (KubeVirt)',
                'vnc',
                'legacy-use-windows-xp-kubevirt',  -- Use Kubernetes service name
                '5900',
                '',
                '',
                '1920',
                '1080',
                'vnc.html',
                '6080',  -- Standard noVNC port
                NOW(),
                NOW(),
                false,
                '',
                '',
                '',
                'windows-xp-vm'
            )
            ON CONFLICT (id) DO NOTHING
        """)
    
    # Insert sample API definitions
    op.execute("""
        INSERT INTO api_definitions (
            id, name, description, created_at, updated_at, is_archived
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
        ON CONFLICT (id) DO NOTHING
    """)
    
    # Insert sample API definition versions
    op.execute("""
        INSERT INTO api_definition_versions (
            id, api_definition_id, version_number, parameters, prompt, 
            prompt_cleanup, response_example, created_at, is_active
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
        ON CONFLICT (id) DO NOTHING
    """)


def downgrade() -> None:
    # Remove sample API definition versions first (due to foreign key constraints)
    op.execute("""
        DELETE FROM api_definition_versions 
        WHERE id IN (
            'b6541819-4853-4bb5-ad42-8bb45067055a',
            'c3c22f1c-24a6-4655-b1b2-e94f6ae11692'
        )
    """)
    
    # Remove sample API definitions
    op.execute("""
        DELETE FROM api_definitions 
        WHERE id IN (
            'de28fb1e-3d79-4357-8db7-4c438b579d95',
            '547ca289-9543-49b2-866b-36e5235f1b0c'
        )
    """)
    
    # Remove sample targets
    op.execute("""
        DELETE FROM targets 
        WHERE id IN (
            '360553ec-2ad2-4dfa-90b5-b6d49b1e7bf3',
            'f47ac10b-58cc-4372-a567-0e02b2c3d479',
            'a8c3d5e2-7b61-4f89-92a4-1e5c8d9f3b27',
            'b5d2f4a8-9c31-4e72-a893-2f6d9e8c4a35'
        )
    """)
