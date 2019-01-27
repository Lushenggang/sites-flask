"""bbs

Revision ID: 5c92eee7f044
Revises: 4953254a0159
Create Date: 2019-01-10 22:21:32.332972

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '5c92eee7f044'
down_revision = '4953254a0159'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('bbs', sa.Column('root_id', sa.Integer(), nullable=True))
    op.drop_column('bbs', 'tree_path')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('bbs', sa.Column('tree_path', mysql.TEXT(), nullable=True))
    op.drop_column('bbs', 'root_id')
    # ### end Alembic commands ###