"""schedule_history

Revision ID: 0000
Revises: 
Create Date: 2022-02-23 17:50:02.469292

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0000'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('workflows_history',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('jobid', sa.String(length=24), nullable=True),
    sa.Column('executionid', sa.String(length=24), nullable=True),
    sa.Column('nb_name', sa.String(), nullable=False),
    sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('elapsed_secs', sa.Float(), nullable=False),
    sa.Column('status', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workflows_history_status'), 'workflows_history', ['status'], unique=False)
    op.create_table('workflows_schedule',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('jobid', sa.String(length=24), nullable=True),
    sa.Column('alias', sa.String(), nullable=True),
    sa.Column('nb_name', sa.String(), nullable=False),
    sa.Column('job_detail', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workflows_schedule_alias'), 'workflows_schedule', ['alias'], unique=True)
    op.create_index(op.f('ix_workflows_schedule_jobid'), 'workflows_schedule', ['jobid'], unique=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_workflows_schedule_jobid'), table_name='workflows_schedule')
    op.drop_index(op.f('ix_workflows_schedule_alias'), table_name='workflows_schedule')
    op.drop_table('workflows_schedule')
    op.drop_index(op.f('ix_workflows_history_status'), table_name='workflows_history')
    op.drop_table('workflows_history')
    # ### end Alembic commands ###
