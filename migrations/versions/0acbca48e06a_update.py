"""update

Revision ID: 0acbca48e06a
Revises: 5c92eee7f044
Create Date: 2019-01-20 21:27:28.931643

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0acbca48e06a'
down_revision = '5c92eee7f044'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('posts', sa.Column('abstract_image', sa.Text(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('posts', 'abstract_image')
    # ### end Alembic commands ###
