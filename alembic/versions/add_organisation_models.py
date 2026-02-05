"""
Add Organisation and related models

Revision ID: add_organisation_models
Revises: 09add0141a24
Create Date: 2025-06-05 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_organisation_models'
down_revision = '09add0141a24'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'organisation',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('name', sa.String),
        sa.Column('orgpath', sa.String),
        sa.Column('parent', sa.Integer, sa.ForeignKey("organisation.id")),
        sa.Column('level', sa.String),
        sa.Column('isSSM', sa.Boolean),
        sa.Column('SSM_functions', sa.String),
        sa.Column('approvers', sa.String),
        sa.Column('country', sa.String)
    )

    op.create_table(
        'institution',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('short_name', sa.String),
        sa.Column('long_name', sa.String),
        sa.Column('country', sa.String),
        sa.Column('country_of_residence', sa.String),
        sa.Column('parent', sa.Integer, sa.ForeignKey("institution.id")),
        sa.Column('is_supervised', sa.Boolean),
        sa.Column('is_', sa.Boolean),
        sa.Column('omi_number', sa.Integer),
        sa.Column('significance', sa.String)
    )

    op.create_table(
        'engagement',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('type', sa.String),
        sa.Column('category', sa.String),
        sa.Column('external_reference', sa.String),
        sa.Column('name', sa.String),
        sa.Column('state', sa.String),
        sa.Column('primary_risk_types', sa.String),
        sa.Column('other_risk_types', sa.String),
        sa.Column('purposes', sa.String),
        sa.Column('start_date', sa.Date),
        sa.Column('planned_start_date', sa.Date),
        sa.Column('institution_id', sa.Integer, sa.ForeignKey("institution.id")),
        sa.Column('supervision_type', sa.String),
        sa.Column('significance', sa.String)
    )

    op.create_table(
        'jst',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('type', sa.String),
        sa.Column('category', sa.String),
        sa.Column('external_reference', sa.String),
        sa.Column('name', sa.String)
    )

    op.create_table(
        'iam_user',
        sa.Column('name', sa.String, primary_key=True, index=True),
        sa.Column('first_name', sa.String),
        sa.Column('last_name', sa.String),
        sa.Column('email', sa.String),
        sa.Column('orgpath', sa.String),
        sa.Column('isSSM', sa.Boolean),
        sa.Column('SSM_functions', sa.String),
        sa.Column('country', sa.String),
        sa.Column('jobTitle', sa.String),
        sa.Column('level', sa.String),
        sa.Column('organisation_id', sa.Integer, sa.ForeignKey("organisation.id")),
        sa.Column('position', sa.String),
        sa.Column('authority', sa.String),
        sa.Column('team', sa.String),
        sa.Column('org_unit_level_a', sa.String),
        sa.Column('ssmnet_author', sa.Boolean, default=False)
    )

    op.create_table(
        'user_engagement',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_username', sa.String, sa.ForeignKey('iam_user.name')),
        sa.Column('engagement_id', sa.Integer, sa.ForeignKey('engagement.id')),
        sa.Column('role', sa.String)  # e.g. 'member', 'lead'
    )

    op.create_table(
        'mission_report',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('engagement_id', sa.Integer, sa.ForeignKey('engagement.id')),
        sa.Column('owner_username', sa.String, sa.ForeignKey('iam_user.name')),
        sa.Column('status', sa.String),  # draft, submitted, approved
        sa.Column('confidentiality', sa.String),
        sa.Column('last_updated_by', sa.String, sa.ForeignKey('iam_user.name'))
    )

def downgrade() -> None:
    op.drop_table('mission_report')
    op.drop_table('user_engagement')
    op.drop_table('iam_user')
    op.drop_table('jst')
    op.drop_table('engagement')
    op.drop_table('institution')
    op.drop_table('organisation')
