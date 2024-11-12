from uuid import UUID, uuid4

from sqlalchemy.orm import Mapped, mapped_column

from db.model.meta import Base


class User(Base):
    __tablename__ = 'user'
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[int]
    username: Mapped[str] = mapped_column(nullable=True)
