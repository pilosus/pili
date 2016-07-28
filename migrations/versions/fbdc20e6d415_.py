"""empty message

Revision ID: fbdc20e6d415
Revises: b1b1f0b1b2f1
Create Date: 2016-07-27 09:14:18.534051

"""

# revision identifiers, used by Alembic.
revision = 'fbdc20e6d415'
down_revision = 'b1b1f0b1b2f1'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('posts', sa.Column('description', sa.String(length=160), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('posts', 'description')
    ### end Alembic commands ###
