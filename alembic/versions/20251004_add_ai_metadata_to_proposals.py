"""Add ai_metadata JSONB column to proposals

Revision ID: 20251004_ai_metadata
Revises: 20251001_1407-0a96be64ebff
Create Date: 2025-10-04 15:20:00.000000

This migration adds the ai_metadata column to store AI reasoning data:
- usage_stats: Token usage and model info
- proven_cases: Proven cases consulted during generation
- deviation_report: Analysis of deviations from proven cases
- assumptions: Design assumptions made by the agent
- alternatives: Alternative technologies considered
- technology_justification: Detailed justifications for selections
- confidence_level: Agent's confidence in the proposal
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251004_ai_metadata'
down_revision = 'migrate_to_fastapi_users'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add ai_metadata JSONB column to proposals table."""
    op.add_column(
        'proposals',
        sa.Column(
            'ai_metadata',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='AI reasoning metadata: usage_stats, proven_cases, deviations, assumptions'
        )
    )
    
    # Create GIN index for efficient JSONB queries
    op.create_index(
        'idx_proposals_ai_metadata',
        'proposals',
        ['ai_metadata'],
        postgresql_using='gin'
    )


def downgrade() -> None:
    """Remove ai_metadata column from proposals table."""
    op.drop_index('idx_proposals_ai_metadata', table_name='proposals')
    op.drop_column('proposals', 'ai_metadata')
