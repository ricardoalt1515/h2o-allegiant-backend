"""Add project_data JSONB column

Revision ID: add_project_data_jsonb
Revises: 
Create Date: 2025-10-01 10:30:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_project_data_jsonb'
down_revision: Union[str, None] = '0a96be64ebff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add project_data JSONB column
    op.add_column('projects', sa.Column(
        'project_data',
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=False,
        server_default='{}'
    ))
    
    # Create GIN index for JSONB
    op.create_index(
        'ix_project_data_gin',
        'projects',
        ['project_data'],
        unique=False,
        postgresql_using='gin'
    )


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_project_data_gin', table_name='projects')
    
    # Drop column
    op.drop_column('projects', 'project_data')
