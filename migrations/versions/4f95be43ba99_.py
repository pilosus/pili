"""empty message

Revision ID: 4f95be43ba99
Revises: fbdc20e6d415
Create Date: 2016-07-28 18:57:29.751383

"""

# revision identifiers, used by Alembic.
revision = '4f95be43ba99'
down_revision = 'fbdc20e6d415'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('suspended', sa.Boolean(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'suspended')
    ### end Alembic commands ###
