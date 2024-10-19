"""Created field roled_id for model User

Revision ID: dc7bb8e9e5f4
Revises: 8b7e3f240f22
Create Date: 2024-10-19 15:31:26.465696

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dc7bb8e9e5f4'
down_revision: Union[str, None] = '8b7e3f240f22'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('image_id', sa.Integer(), nullable=True))
    op.add_column('user', sa.Column('role_id', sa.Integer(), nullable=False))
    op.drop_constraint('user_image_fkey', 'user', type_='foreignkey')
    op.create_foreign_key(None, 'user', 'media', ['image_id'], ['id'])
    op.create_foreign_key(None, 'user', 'roles', ['role_id'], ['id'])
    op.drop_column('user', 'image')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('image', sa.INTEGER(), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'user', type_='foreignkey')
    op.drop_constraint(None, 'user', type_='foreignkey')
    op.create_foreign_key('user_image_fkey', 'user', 'media', ['image'], ['id'])
    op.drop_column('user', 'role_id')
    op.drop_column('user', 'image_id')
    # ### end Alembic commands ###
