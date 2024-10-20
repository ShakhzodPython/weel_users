"""Setup migrations for weel.users

Revision ID: d9ff0ab46bd9
Revises: 
Create Date: 2024-10-20 18:38:23.320702

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9ff0ab46bd9'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('media',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('url', sa.String(length=225), nullable=False),
    sa.Column('filename', sa.String(length=225), nullable=False),
    sa.Column('uploaded_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('roles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=50), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('title')
    )
    op.create_table('user',
    sa.Column('uuid', sa.UUID(), nullable=False),
    sa.Column('username', sa.String(length=100), nullable=True),
    sa.Column('hash_password', sa.String(length=128), nullable=True),
    sa.Column('phone_number', sa.String(length=11), nullable=False),
    sa.Column('full_name', sa.String(length=100), nullable=True),
    sa.Column('email', sa.String(length=100), nullable=True),
    sa.Column('image_id', sa.Integer(), nullable=True),
    sa.Column('role_id', sa.Integer(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('registered_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['image_id'], ['media.id'], ),
    sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
    sa.PrimaryKeyConstraint('uuid'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('phone_number'),
    sa.UniqueConstraint('username')
    )
    op.create_index(op.f('ix_user_uuid'), 'user', ['uuid'], unique=False)
    op.create_table('cards',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_uuid', sa.UUID(), nullable=False),
    sa.Column('card_number_hashed', sa.String(length=225), nullable=False),
    sa.Column('expiry_date_hashed', sa.String(length=225), nullable=False),
    sa.Column('is_blacklisted', sa.Boolean(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_uuid'], ['user.uuid'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('card_number_hashed')
    )
    op.create_table('work_schedule',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_uuid', sa.UUID(), nullable=False),
    sa.Column('day_of_week', sa.String(), nullable=False),
    sa.Column('start_time', sa.Integer(), nullable=False),
    sa.Column('end_time', sa.Integer(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_uuid'], ['user.uuid'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('wallet',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_uuid', sa.UUID(), nullable=False),
    sa.Column('card_id', sa.Integer(), nullable=False),
    sa.Column('profit', sa.Integer(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['card_id'], ['cards.id'], ),
    sa.ForeignKeyConstraint(['user_uuid'], ['user.uuid'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('wallet')
    op.drop_table('work_schedule')
    op.drop_table('cards')
    op.drop_index(op.f('ix_user_uuid'), table_name='user')
    op.drop_table('user')
    op.drop_table('roles')
    op.drop_table('media')
    # ### end Alembic commands ###
