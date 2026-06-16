from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Boolean
from sqlalchemy import ForeignKey
from sqlalchemy import UniqueConstraint
from sqlalchemy import DateTime
from sqlalchemy.sql import func

from database import Base


class User(Base):

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    nome = Column(String, nullable=False)

    apelido = Column(String, nullable=False)

    email = Column(String, unique=True, nullable=False)

    telefone = Column(String, nullable=True)

    senha = Column(String, nullable=False)

    receber_notificacoes = Column(
        Boolean,
        default=True
    )

    is_blocked = Column(
        Boolean,
        default=False
    )

    avatar_id = Column(
        Integer,
        ForeignKey("avatar_items.id"),
        nullable=True
    )

    avatar_url = Column(
        String,
        nullable=True,
        default="assets/avatars/default-avatar.png"
    )


class PasswordRecoveryRequest(Base):

    __tablename__ = "password_recovery_requests"

    id = Column(Integer, primary_key=True, index=True)

    email = Column(String, nullable=False)

    telefone = Column(String, nullable=True)

    status = Column(
        String,
        nullable=False,
        default="pending"
    )

    created_at = Column(
        DateTime,
        server_default=func.now()
    )

    resolved_at = Column(
        DateTime,
        nullable=True
    )

class ReadingProgress(Base):

    __tablename__ = "reading_progress"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    chapter = Column(Integer, nullable=False)

    page = Column(Integer, nullable=False)


class UserUnlock(Base):

    __tablename__ = "user_unlocks"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    unlock_type = Column(String, nullable=False)

    unlock_key = Column(String, nullable=False)


class Chapter(Base):

    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, index=True)

    number = Column(Integer, unique=True, nullable=False, index=True)

    title = Column(String, nullable=False)

    description = Column(String, nullable=True)

    cover_image = Column(String, nullable=True)

    release_date = Column(String, nullable=True)

    is_published = Column(Boolean, default=True)


class ChapterPage(Base):

    __tablename__ = "chapter_pages"

    __table_args__ = (
        UniqueConstraint(
            "chapter_id",
            "page_number",
            name="uq_chapter_page"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False)

    page_number = Column(Integer, nullable=False)

    image_url = Column(String, nullable=False)


class AvatarItem(Base):

    __tablename__ = "avatar_items"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)

    description = Column(String, nullable=True)

    image_url = Column(String, nullable=True)

    rarity = Column(String, nullable=False, default="Comum")

    source_type = Column(String, nullable=False, default="initial")

    unlock_type = Column(String, nullable=True)

    unlock_key = Column(String, nullable=True)

    price = Column(Integer, nullable=False, default=0)

    is_active = Column(Boolean, default=True)

class UserAvatarUnlock(Base):

    __tablename__ = "user_avatar_unlocks"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "avatar_id",
            name="uq_user_avatar_unlock"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    avatar_id = Column(Integer, ForeignKey("avatar_items.id"), nullable=False)

    unlocked_at = Column(
        DateTime,
        server_default=func.now()
    )


class OutfitItem(Base):

    __tablename__ = "outfit_items"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)

    description = Column(String, nullable=True)

    image_url = Column(String, nullable=True)

    rarity = Column(String, nullable=False, default="Comum")

    outfit_type = Column(String, nullable=False, default="clothing")

    source_type = Column(String, nullable=False, default="chapter_reward")

    unlock_type = Column(String, nullable=True)

    unlock_key = Column(String, nullable=True)

    price = Column(Integer, nullable=False, default=0)

    is_active = Column(Boolean, default=True)


class UserOutfitUnlock(Base):

    __tablename__ = "user_outfit_unlocks"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "outfit_id",
            name="uq_user_outfit_unlock"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    outfit_id = Column(Integer, ForeignKey("outfit_items.id"), nullable=False)

    is_equipped = Column(Boolean, default=False)

    unlocked_at = Column(
        DateTime,
        server_default=func.now()
    )
