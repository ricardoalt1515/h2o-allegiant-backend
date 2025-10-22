"""
Migrate to FastAPI Users

Revision ID: migrate_to_fastapi_users
Revises: (auto-fill with your latest revision)
Create Date: 2025-10-02

This migration adapts the existing users table for FastAPI Users:
1. Renames password_hash -> hashed_password
2. Renames is_admin -> is_superuser
3. Adds is_verified column
4. Preserves all existing data

Best Practices:
    - Backward compatible
    - Preserves existing data
    - Sets sensible defaults
    - Marks existing users as verified
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision = 'migrate_to_fastapi_users'
down_revision = 'add_project_data_jsonb'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Migrate users table to FastAPI Users schema.
    
    Changes:
        - password_hash → hashed_password (FastAPI Users convention)
        - is_admin → is_superuser (FastAPI Users convention)
        - Add is_verified (required by FastAPI Users, default False)
    
    Data Preservation:
        - All existing users kept
        - Existing users marked as verified (trusted)
        - All relationships maintained
    """
    
    # Step 1: Rename password_hash to hashed_password
    # This is the FastAPI Users naming convention
    op.alter_column(
        'users',
        'password_hash',
        new_column_name='hashed_password',
        existing_type=sa.String(255),
        existing_nullable=False,
        existing_comment='Bcrypt hashed password'
    )
    
    # Step 2: Rename is_admin to is_superuser
    # FastAPI Users uses is_superuser instead of is_admin
    op.alter_column(
        'users',
        'is_admin',
        new_column_name='is_superuser',
        existing_type=sa.Boolean(),
        existing_nullable=False,
        existing_server_default='false'
    )
    
    # Step 3: Add is_verified column
    # Required by FastAPI Users for email verification
    # Default False for new users, but we'll set True for existing users
    op.add_column(
        'users',
        sa.Column(
            'is_verified',
            sa.Boolean(),
            nullable=False,
            server_default='false',
            comment='Whether user email is verified'
        )
    )
    
    # Step 4: Mark existing users as verified
    # Assumption: existing users are trusted and should be verified
    op.execute(
        "UPDATE users SET is_verified = true WHERE created_at < NOW()"
    )


def downgrade() -> None:
    """
    Rollback FastAPI Users migration.
    
    Restores original schema:
        - hashed_password → password_hash
        - is_superuser → is_admin
        - Removes is_verified
    """
    
    # Remove is_verified column
    op.drop_column('users', 'is_verified')
    
    # Rename is_superuser back to is_admin
    op.alter_column(
        'users',
        'is_superuser',
        new_column_name='is_admin',
        existing_type=sa.Boolean(),
        existing_nullable=False
    )
    
    # Rename hashed_password back to password_hash
    op.alter_column(
        'users',
        'hashed_password',
        new_column_name='password_hash',
        existing_type=sa.String(255),
        existing_nullable=False
    )
