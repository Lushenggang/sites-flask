"""empty message

Revision ID: 4953254a0159
Revises: e7229e83f43d
Create Date: 2019-01-06 15:26:49.286171

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4953254a0159'
down_revision = 'e7229e83f43d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('bbs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('body', sa.Text(), nullable=True),
    sa.Column('author_id', sa.Integer(), nullable=True),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.Column('tree_path', sa.Text(), nullable=True),
    sa.Column('response_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['response_id'], ['bbs.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bbs_timestamp'), 'bbs', ['timestamp'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_bbs_timestamp'), table_name='bbs')
    op.drop_table('bbs')
    # ### end Alembic commands ###
