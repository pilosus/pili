"""empty message

Revision ID: 3bb5e755df4
Revises: 4002c049330
Create Date: 2016-04-16 16:47:12.493927

"""

# revision identifiers, used by Alembic.
revision = '3bb5e755df4'
down_revision = '4002c049330'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('uploads') as batch_op:
        batch_op.drop_column('title')
        batch_op.add_column(sa.Column('title', sa.String(length=128), nullable=True))
        batch_op.drop_column('id')
        batch_op.alter_column('filename',
                              existing_type=sa.VARCHAR(length=64),
                              nullable=False)
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('uploads', 'filename',
               existing_type=sa.VARCHAR(length=64),
               nullable=True)
    op.add_column('uploads', sa.Column('id', sa.INTEGER(), nullable=False))
    op.drop_column('uploads', 'title')
    ### end Alembic commands ###
