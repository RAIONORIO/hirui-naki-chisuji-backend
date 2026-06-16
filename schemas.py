from typing import Optional

from pydantic import BaseModel


class UserCreate(BaseModel):

    nome: str

    apelido: str

    email: str

    telefone: str

    senha: str


class LoginRequest(BaseModel):

    email: str

    senha: str


class UserResponse(BaseModel):

    id: int

    nome: str

    apelido: str

    email: str

    telefone: Optional[str] = None

    receber_notificacoes: bool

    is_blocked: bool

    avatar_id: Optional[int] = None

    avatar_url: Optional[str] = None

    class Config:

        from_attributes = True


class UserProfileUpdate(BaseModel):

    nome: str

    apelido: str

    email: str

    telefone: Optional[str] = None


class UserPasswordUpdate(BaseModel):

    senha_atual: str

    nova_senha: str

    confirmar_senha: str


class AdminPasswordReset(BaseModel):

    nova_senha: str

    confirmar_senha: str


class PasswordRecoveryRequestCreate(BaseModel):

    email: str

    telefone: Optional[str] = None


class PasswordRecoveryRequestResolve(BaseModel):

    status: str = "resolved"


class PasswordRecoveryRequestResponse(BaseModel):

    id: int

    email: str

    telefone: Optional[str] = None

    status: str

    created_at: Optional[str] = None

    resolved_at: Optional[str] = None

    class Config:

        from_attributes = True


class UserAvatarSelect(BaseModel):

    avatar_id: int


class ReadingProgressCreate(BaseModel):

    user_id: int

    chapter: int

    page: int


class ReadingProgressResponse(BaseModel):

    id: int

    user_id: int

    chapter: int

    page: int

    class Config:

        from_attributes = True


class UserUnlockCreate(BaseModel):

    user_id: int

    unlock_type: str

    unlock_key: str


class UserUnlockResponse(BaseModel):

    id: int

    user_id: int

    unlock_type: str

    unlock_key: str

    class Config:

        from_attributes = True


class ChapterCreate(BaseModel):

    number: int

    title: str

    description: Optional[str] = None

    cover_image: Optional[str] = None

    release_date: Optional[str] = None

    is_published: bool = True


class ChapterUpdate(BaseModel):

    number: Optional[int] = None

    title: Optional[str] = None

    description: Optional[str] = None

    cover_image: Optional[str] = None

    release_date: Optional[str] = None

    is_published: Optional[bool] = None


class ChapterResponse(BaseModel):

    id: int

    number: int

    title: str

    description: Optional[str]

    cover_image: Optional[str]

    release_date: Optional[str]

    is_published: bool

    class Config:

        from_attributes = True


class ChapterPageCreate(BaseModel):

    page_number: int

    image_url: str


class ChapterPageResponse(BaseModel):

    id: int

    chapter_id: int

    page_number: int

    image_url: str

    class Config:

        from_attributes = True


class AvatarItemCreate(BaseModel):

    name: str

    description: Optional[str] = None

    image_url: Optional[str] = None

    rarity: str = "Comum"

    source_type: str = "initial"

    unlock_type: Optional[str] = None

    unlock_key: Optional[str] = None

    price: int = 0

    is_active: bool = True


class AvatarItemUpdate(BaseModel):

    name: Optional[str] = None

    description: Optional[str] = None

    image_url: Optional[str] = None

    rarity: Optional[str] = None

    source_type: Optional[str] = None

    unlock_type: Optional[str] = None

    unlock_key: Optional[str] = None

    price: Optional[int] = None

    is_active: Optional[bool] = None


class AvatarItemResponse(BaseModel):

    id: int

    name: str

    description: Optional[str] = None

    image_url: Optional[str] = None

    rarity: str

    source_type: str

    unlock_type: Optional[str] = None

    unlock_key: Optional[str] = None

    price: int

    is_active: bool

    class Config:

        from_attributes = True


class UserAvatarUnlockResponse(BaseModel):

    id: int

    user_id: int

    avatar_id: int

    class Config:

        from_attributes = True


class OutfitItemCreate(BaseModel):

    name: str

    description: Optional[str] = None

    image_url: Optional[str] = None

    rarity: str = "Comum"

    outfit_type: str = "clothing"

    source_type: str = "chapter_reward"

    unlock_type: Optional[str] = None

    unlock_key: Optional[str] = None

    price: int = 0

    is_active: bool = True


class OutfitItemUpdate(BaseModel):

    name: Optional[str] = None

    description: Optional[str] = None

    image_url: Optional[str] = None

    rarity: Optional[str] = None

    outfit_type: Optional[str] = None

    source_type: Optional[str] = None

    unlock_type: Optional[str] = None

    unlock_key: Optional[str] = None

    price: Optional[int] = None

    is_active: Optional[bool] = None


class OutfitItemResponse(BaseModel):

    id: int

    name: str

    description: Optional[str] = None

    image_url: Optional[str] = None

    rarity: str

    outfit_type: str

    source_type: str

    unlock_type: Optional[str] = None

    unlock_key: Optional[str] = None

    price: int

    is_active: bool

    is_unlocked: Optional[bool] = False

    is_equipped: Optional[bool] = False

    class Config:

        from_attributes = True


class UserOutfitUnlockResponse(BaseModel):

    id: int

    user_id: int

    outfit_id: int

    is_equipped: bool = False

    class Config:

        from_attributes = True


class UserOutfitSelect(BaseModel):

    outfit_id: int