import os
import shutil
import time
import sqlite3
from datetime import datetime
from fastapi import FastAPI
from fastapi import File
from fastapi import Form
from fastapi import UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from database import Base
from database import engine
from database import SessionLocal

from models import User
from models import ReadingProgress
from models import UserUnlock
from models import Chapter
from models import ChapterPage
from models import AvatarItem
from models import UserAvatarUnlock
from models import PasswordRecoveryRequest
from models import OutfitItem
from models import UserOutfitUnlock

from schemas import UserCreate
from schemas import LoginRequest
from schemas import ReadingProgressCreate
from schemas import UserUnlockCreate
from schemas import ChapterCreate
from schemas import ChapterUpdate
from schemas import ChapterPageCreate
from schemas import UserProfileUpdate
from schemas import UserPasswordUpdate
from schemas import AdminPasswordReset
from schemas import PasswordRecoveryRequestCreate
from schemas import PasswordRecoveryRequestResolve
from schemas import UserAvatarSelect
from schemas import AvatarItemCreate
from schemas import AvatarItemUpdate
from schemas import OutfitItemCreate
from schemas import OutfitItemUpdate
from schemas import UserOutfitSelect
# =========================================
# ADMIN
# =========================================

ADMIN_EMAIL = "raionorio0204@admin.com"


def check_is_admin(email: str):

    if not email:

        return False

    return email.strip().lower() == ADMIN_EMAIL

# =========================================
# APP
# =========================================

app = FastAPI()

# =========================================
# CRIAR PASTAS NECESSÁRIAS
# =========================================

os.makedirs("manga", exist_ok=True)
os.makedirs("manga/covers", exist_ok=True)
os.makedirs("manga/avatars", exist_ok=True)
os.makedirs("manga/outfits", exist_ok=True)
# =========================================
# CRIAR TABELAS
# =========================================

Base.metadata.create_all(bind=engine)


# =========================================
# AJUSTES DO BANCO LOCAL
# =========================================

def ensure_local_database_columns():

    connection = sqlite3.connect("hirui.db")

    cursor = connection.cursor()

    cursor.execute("PRAGMA table_info(users)")

    columns = [column[1] for column in cursor.fetchall()]

    if "is_blocked" not in columns:

        cursor.execute(
            "ALTER TABLE users ADD COLUMN is_blocked BOOLEAN DEFAULT 0"
        )

        connection.commit()

    if "avatar_id" not in columns:

        cursor.execute(
            "ALTER TABLE users ADD COLUMN avatar_id INTEGER"
        )

        connection.commit()

    if "avatar_url" not in columns:

        cursor.execute(
            "ALTER TABLE users ADD COLUMN avatar_url TEXT DEFAULT 'assets/avatars/default-avatar.png'"
        )

        connection.commit()

    connection.close()


ensure_local_database_columns()

Base.metadata.create_all(bind=engine)

def ensure_default_avatar_item():
    def ensure_initial_outfit_items():

        db = SessionLocal()

        try:

            initial_outfits = [
                {
                    "name": "Roupa de Aldeão Onizuka",
                    "description": "Traje simples usado pelos aldeões ligados ao território do Clã Onizuka.",
                    "image_url": None,
                    "rarity": "Comum",
                    "outfit_type": "clothing",
                    "source_type": "chapter_reward",
                    "unlock_type": "chapter_finish",
                    "unlock_key": "cap1",
                    "price": 0,
                    "is_active": True
                },
                {
                    "name": "Roupa de Soldado Onizuka",
                    "description": "Traje de soldado associado às forças do Clã Onizuka.",
                    "image_url": None,
                    "rarity": "Incomum",
                    "outfit_type": "clothing",
                    "source_type": "chapter_reward",
                    "unlock_type": "chapter_finish",
                    "unlock_key": "cap1",
                    "price": 0,
                    "is_active": True
                }
            ]

            for outfit_data in initial_outfits:

                existing_outfit = (
                    db.query(OutfitItem)
                    .filter(OutfitItem.name == outfit_data["name"])
                    .first()
                )

                if existing_outfit:
                    continue

                new_outfit = OutfitItem(
                    name=outfit_data["name"],
                    description=outfit_data["description"],
                    image_url=outfit_data["image_url"],
                    rarity=outfit_data["rarity"],
                    outfit_type=outfit_data["outfit_type"],
                    source_type=outfit_data["source_type"],
                    unlock_type=outfit_data["unlock_type"],
                    unlock_key=outfit_data["unlock_key"],
                    price=outfit_data["price"],
                    is_active=outfit_data["is_active"]
                )

                db.add(new_outfit)

            db.commit()

        finally:

            db.close()

    ensure_initial_outfit_items()
    db = SessionLocal()

    try:

        default_avatar = (
            db.query(AvatarItem)
            .filter(AvatarItem.source_type == "initial")
            .filter(AvatarItem.name == "Avatar Padrão")
            .first()
        )

        if default_avatar:

            return

        new_avatar = AvatarItem(
            name="Avatar Padrão",
            description="Avatar inicial concedido a todos os leitores.",
            image_url="assets/avatars/default-avatar.png",
            rarity="Comum",
            source_type="initial",
            unlock_type="initial",
            unlock_key="default-avatar",
            price=0,
            is_active=True
        )

        db.add(new_avatar)

        db.commit()

    finally:

        db.close()


ensure_default_avatar_item()

# =========================================
# CORS
# =========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================
# DATABASE
# =========================================

def get_db():

    db = SessionLocal()

    try:

        yield db

    finally:

        db.close()

# =========================================
# ARQUIVOS ESTÁTICOS
# =========================================

app.mount(
    "/manga",
    StaticFiles(directory="manga"),
    name="manga"
)

# =========================================
# HOME
# =========================================

@app.get("/")
def home():

    return {
        "message": "Hirui Naki Chisuji Backend Online"
    }

# =========================================
# CAPÍTULOS - LEITURA PÚBLICA
# =========================================

@app.get("/chapters")
def get_chapters():

    db = SessionLocal()

    try:

        chapters = (
            db.query(Chapter)
            .filter(Chapter.is_published == True)
            .order_by(Chapter.number)
            .all()
        )

        return {
            "success": True,
            "chapters": [
                {
                    "id": chapter.id,
                    "number": chapter.number,
                    "title": chapter.title,
                    "description": chapter.description,
                    "cover_image": chapter.cover_image,
                    "release_date": chapter.release_date,
                    "is_published": chapter.is_published
                }
                for chapter in chapters
            ]
        }

    finally:

        db.close()


@app.get("/chapters/{chapter_number}/pages")
def get_chapter_pages(chapter_number: int):

    db = SessionLocal()

    try:

        chapter = (
            db.query(Chapter)
            .filter(Chapter.number == chapter_number)
            .filter(Chapter.is_published == True)
            .first()
        )

        if not chapter:

            return {
                "success": False,
                "message": "Capítulo não encontrado"
            }

        pages = (
            db.query(ChapterPage)
            .filter(ChapterPage.chapter_id == chapter.id)
            .order_by(ChapterPage.page_number)
            .all()
        )

        return {
            "success": True,
            "chapter": {
                "id": chapter.id,
                "number": chapter.number,
                "title": chapter.title
            },
            "pages": [
                {
                    "id": page.id,
                    "page_number": page.page_number,
                    "image_url": page.image_url
                }
                for page in pages
            ]
        }

    finally:

        db.close()


@app.get("/chapter/{chapter}/page/{page}")
def get_page(chapter: int, page: int):

    db = SessionLocal()

    try:

        if page < 1:

            return {
                "success": False,
                "chapter": chapter,
                "page": page,
                "image": None,
                "message": "Número de página inválido"
            }

        chapter_record = (
            db.query(Chapter)
            .filter(Chapter.number == chapter)
            .filter(Chapter.is_published == True)
            .first()
        )

        if not chapter_record:

            return {
                "success": False,
                "chapter": chapter,
                "page": page,
                "image": None,
                "message": "Capítulo não encontrado ou não publicado"
            }

        page_record = (
            db.query(ChapterPage)
            .filter(ChapterPage.chapter_id == chapter_record.id)
            .filter(ChapterPage.page_number == page)
            .first()
        )

        if not page_record:

            return {
                "success": False,
                "chapter": chapter,
                "page": page,
                "image": None,
                "message": "Página não cadastrada no banco",
                "end_of_chapter": True
            }

        next_page = (
            db.query(ChapterPage)
            .filter(ChapterPage.chapter_id == chapter_record.id)
            .filter(ChapterPage.page_number > page)
            .order_by(ChapterPage.page_number)
            .first()
        )

        previous_page = (
            db.query(ChapterPage)
            .filter(ChapterPage.chapter_id == chapter_record.id)
            .filter(ChapterPage.page_number < page)
            .order_by(ChapterPage.page_number.desc())
            .first()
        )

        return {
            "success": True,
            "chapter": chapter,
            "page": page,
            "image": page_record.image_url,
            "has_next_page": next_page is not None,
            "has_previous_page": previous_page is not None
        }

    finally:

        db.close()
# =========================================
# ADMIN - GERENCIAR CAPÍTULOS
# =========================================

@app.get("/admin/chapters")
def admin_get_chapters():

    db = SessionLocal()

    try:

        chapters = (
            db.query(Chapter)
            .order_by(Chapter.number)
            .all()
        )

        return {
            "success": True,
            "chapters": [
                {
                    "id": chapter.id,
                    "number": chapter.number,
                    "title": chapter.title,
                    "description": chapter.description,
                    "cover_image": chapter.cover_image,
                    "release_date": chapter.release_date,
                    "is_published": chapter.is_published
                }
                for chapter in chapters
            ]
        }

    finally:

        db.close()


@app.post("/admin/chapters")
def admin_create_chapter(chapter: ChapterCreate):

    db = SessionLocal()

    try:

        existing_chapter = (
            db.query(Chapter)
            .filter(Chapter.number == chapter.number)
            .first()
        )

        if existing_chapter:

            return {
                "success": False,
                "message": "Já existe um capítulo com esse número"
            }

        new_chapter = Chapter(
            number=chapter.number,
            title=chapter.title,
            description=chapter.description,
            cover_image=chapter.cover_image,
            release_date=chapter.release_date,
            is_published=chapter.is_published
        )

        db.add(new_chapter)

        db.commit()

        db.refresh(new_chapter)

        chapter_folder = f"manga/cap{new_chapter.number}"

        os.makedirs(chapter_folder, exist_ok=True)

        return {
            "success": True,
            "message": "Capítulo criado com sucesso",
            "chapter": {
                "id": new_chapter.id,
                "number": new_chapter.number,
                "title": new_chapter.title,
                "description": new_chapter.description,
                "cover_image": new_chapter.cover_image,
                "release_date": new_chapter.release_date,
                "is_published": new_chapter.is_published
            }
        }

    finally:

        db.close()


@app.put("/admin/chapters/{chapter_id}")
def admin_update_chapter(chapter_id: int, data: ChapterUpdate):

    db = SessionLocal()

    try:

        chapter = (
            db.query(Chapter)
            .filter(Chapter.id == chapter_id)
            .first()
        )

        if not chapter:

            return {
                "success": False,
                "message": "Capítulo não encontrado"
            }

        if data.number is not None and data.number != chapter.number:

            existing_chapter = (
                db.query(Chapter)
                .filter(Chapter.number == data.number)
                .first()
            )

            if existing_chapter:

                return {
                    "success": False,
                    "message": "Já existe um capítulo com esse número"
                }

            chapter.number = data.number

        if data.title is not None:

            chapter.title = data.title

        if data.description is not None:

            chapter.description = data.description

        if data.cover_image is not None:

            chapter.cover_image = data.cover_image

        if data.release_date is not None:

            chapter.release_date = data.release_date

        if data.is_published is not None:

            chapter.is_published = data.is_published

        db.commit()

        db.refresh(chapter)

        return {
            "success": True,
            "message": "Capítulo atualizado com sucesso",
            "chapter": {
                "id": chapter.id,
                "number": chapter.number,
                "title": chapter.title,
                "description": chapter.description,
                "cover_image": chapter.cover_image,
                "release_date": chapter.release_date,
                "is_published": chapter.is_published
            }
        }

    finally:

        db.close()

@app.post("/admin/chapters/{chapter_id}/cover/upload")
async def admin_upload_chapter_cover(
    chapter_id: int,
    cover: UploadFile = File(...)
):

    db = SessionLocal()

    try:

        chapter = (
            db.query(Chapter)
            .filter(Chapter.id == chapter_id)
            .first()
        )

        if not chapter:

            return {
                "success": False,
                "message": "Capítulo não encontrado"
            }

        allowed_extensions = [".jpg", ".jpeg", ".png", ".webp"]

        file_extension = os.path.splitext(cover.filename)[1].lower()

        if file_extension not in allowed_extensions:

            return {
                "success": False,
                "message": "Formato inválido. Use JPG, JPEG, PNG ou WEBP."
            }

        cover_folder = "manga/covers"

        os.makedirs(cover_folder, exist_ok=True)

        timestamp = int(time.time())

        file_name = f"chapter-{chapter.id}-cover-{timestamp}{file_extension}"

        file_path = os.path.join(cover_folder, file_name)

        with open(file_path, "wb") as buffer:

            shutil.copyfileobj(cover.file, buffer)

        cover_url = (
            f"http://127.0.0.1:8000/"
            f"manga/covers/{file_name}"
        )

        chapter.cover_image = cover_url

        db.commit()

        db.refresh(chapter)

        return {
            "success": True,
            "message": "Capa enviada com sucesso",
            "chapter": {
                "id": chapter.id,
                "number": chapter.number,
                "title": chapter.title,
                "description": chapter.description,
                "cover_image": chapter.cover_image,
                "release_date": chapter.release_date,
                "is_published": chapter.is_published
            }
        }

    finally:

        db.close()

@app.delete("/admin/chapters/{chapter_id}")
def admin_delete_chapter(chapter_id: int):

    db = SessionLocal()

    try:

        chapter = (
            db.query(Chapter)
            .filter(Chapter.id == chapter_id)
            .first()
        )

        if not chapter:

            return {
                "success": False,
                "message": "Capítulo não encontrado"
            }

        (
            db.query(ChapterPage)
            .filter(ChapterPage.chapter_id == chapter.id)
            .delete()
        )

        db.delete(chapter)

        db.commit()

        return {
            "success": True,
            "message": "Capítulo removido com sucesso"
        }

    finally:

        db.close()

# =========================================
# ADMIN - GERENCIAR PÁGINAS
# =========================================

@app.get("/admin/chapters/{chapter_id}/pages")
def admin_get_chapter_pages(chapter_id: int):

    db = SessionLocal()

    try:

        chapter = (
            db.query(Chapter)
            .filter(Chapter.id == chapter_id)
            .first()
        )

        if not chapter:

            return {
                "success": False,
                "message": "Capítulo não encontrado"
            }

        pages = (
            db.query(ChapterPage)
            .filter(ChapterPage.chapter_id == chapter.id)
            .order_by(ChapterPage.page_number)
            .all()
        )

        return {
            "success": True,
            "chapter": {
                "id": chapter.id,
                "number": chapter.number,
                "title": chapter.title
            },
            "pages": [
                {
                    "id": page.id,
                    "chapter_id": page.chapter_id,
                    "page_number": page.page_number,
                    "image_url": page.image_url
                }
                for page in pages
            ]
        }

    finally:

        db.close()


@app.post("/admin/chapters/{chapter_id}/pages")
def admin_create_chapter_page(chapter_id: int, page: ChapterPageCreate):

    db = SessionLocal()

    try:

        chapter = (
            db.query(Chapter)
            .filter(Chapter.id == chapter_id)
            .first()
        )

        if not chapter:

            return {
                "success": False,
                "message": "Capítulo não encontrado"
            }

        existing_page = (
            db.query(ChapterPage)
            .filter(ChapterPage.chapter_id == chapter.id)
            .filter(ChapterPage.page_number == page.page_number)
            .first()
        )

        if existing_page:

            existing_page.image_url = page.image_url

            db.commit()

            db.refresh(existing_page)

            return {
                "success": True,
                "message": "Página atualizada com sucesso",
                "page": {
                    "id": existing_page.id,
                    "chapter_id": existing_page.chapter_id,
                    "page_number": existing_page.page_number,
                    "image_url": existing_page.image_url
                }
            }

        new_page = ChapterPage(
            chapter_id=chapter.id,
            page_number=page.page_number,
            image_url=page.image_url
        )

        db.add(new_page)

        db.commit()

        db.refresh(new_page)

        return {
            "success": True,
            "message": "Página criada com sucesso",
            "page": {
                "id": new_page.id,
                "chapter_id": new_page.chapter_id,
                "page_number": new_page.page_number,
                "image_url": new_page.image_url
            }
        }

    finally:

        db.close()


@app.post("/admin/chapters/{chapter_id}/pages/upload")
async def admin_upload_chapter_page(
    chapter_id: int,
    page_number: int = Form(...),
    image: UploadFile = File(...)
):

    db = SessionLocal()

    try:

        chapter = (
            db.query(Chapter)
            .filter(Chapter.id == chapter_id)
            .first()
        )

        if not chapter:

            return {
                "success": False,
                "message": "Capítulo não encontrado"
            }

        allowed_extensions = [".jpg", ".jpeg", ".png", ".webp"]

        file_extension = os.path.splitext(image.filename)[1].lower()

        if file_extension not in allowed_extensions:

            return {
                "success": False,
                "message": "Formato inválido. Use JPG, JPEG, PNG ou WEBP."
            }

        chapter_folder = f"manga/cap{chapter.number}"

        os.makedirs(chapter_folder, exist_ok=True)

        file_name = f"{page_number}{file_extension}"

        file_path = os.path.join(chapter_folder, file_name)

        with open(file_path, "wb") as buffer:

            shutil.copyfileobj(image.file, buffer)

        image_url = (
            f"http://127.0.0.1:8000/"
            f"manga/cap{chapter.number}/{file_name}"
        )

        existing_page = (
            db.query(ChapterPage)
            .filter(ChapterPage.chapter_id == chapter.id)
            .filter(ChapterPage.page_number == page_number)
            .first()
        )

        if existing_page:

            existing_page.image_url = image_url

            db.commit()

            db.refresh(existing_page)

            return {
                "success": True,
                "message": "Imagem da página atualizada com sucesso",
                "page": {
                    "id": existing_page.id,
                    "chapter_id": existing_page.chapter_id,
                    "page_number": existing_page.page_number,
                    "image_url": existing_page.image_url
                }
            }

        new_page = ChapterPage(
            chapter_id=chapter.id,
            page_number=page_number,
            image_url=image_url
        )

        db.add(new_page)

        db.commit()

        db.refresh(new_page)

        return {
            "success": True,
            "message": "Imagem da página enviada com sucesso",
            "page": {
                "id": new_page.id,
                "chapter_id": new_page.chapter_id,
                "page_number": new_page.page_number,
                "image_url": new_page.image_url
            }
        }

    finally:

        db.close()

@app.post("/admin/chapters/{chapter_id}/pages/bulk-upload")
async def admin_bulk_upload_chapter_pages(
    chapter_id: int,
    images: list[UploadFile] = File(...)
):

    db = SessionLocal()

    try:

        chapter = (
            db.query(Chapter)
            .filter(Chapter.id == chapter_id)
            .first()
        )

        if not chapter:

            return {
                "success": False,
                "message": "Capítulo não encontrado"
            }

        if not images:

            return {
                "success": False,
                "message": "Nenhuma imagem enviada"
            }

        allowed_extensions = [".jpg", ".jpeg", ".png", ".webp"]

        validated_images = []

        used_page_numbers = set()

        for image in images:

            file_extension = os.path.splitext(image.filename)[1].lower()

            if file_extension not in allowed_extensions:

                return {
                    "success": False,
                    "message": f"Formato inválido no arquivo {image.filename}. Use JPG, JPEG, PNG ou WEBP."
                }

            file_name_without_extension = os.path.splitext(image.filename)[0]

            if not file_name_without_extension.isdigit():

                return {
                    "success": False,
                    "message": (
                        f"O arquivo {image.filename} não possui nome numérico. "
                        "Use nomes como 1.jpg, 2.jpg, 3.jpg ou 01.jpg, 02.jpg."
                    )
                }

            page_number = int(file_name_without_extension)

            if page_number < 1:

                return {
                    "success": False,
                    "message": f"O arquivo {image.filename} possui número de página inválido."
                }

            if page_number in used_page_numbers:

                return {
                    "success": False,
                    "message": f"Existe mais de um arquivo para a página {page_number}."
                }

            used_page_numbers.add(page_number)

            validated_images.append({
                "page_number": page_number,
                "file_extension": file_extension,
                "image": image
            })

        validated_images.sort(key=lambda item: item["page_number"])

        chapter_folder = f"manga/cap{chapter.number}"

        os.makedirs(chapter_folder, exist_ok=True)

        created_pages = 0

        updated_pages = 0

        saved_pages = []

        for item in validated_images:

            page_number = item["page_number"]

            file_extension = item["file_extension"]

            image = item["image"]

            file_name = f"{page_number}{file_extension}"

            file_path = os.path.join(chapter_folder, file_name)

            image.file.seek(0)

            with open(file_path, "wb") as buffer:

                shutil.copyfileobj(image.file, buffer)

            image_url = (
                f"http://127.0.0.1:8000/"
                f"manga/cap{chapter.number}/{file_name}"
            )

            existing_page = (
                db.query(ChapterPage)
                .filter(ChapterPage.chapter_id == chapter.id)
                .filter(ChapterPage.page_number == page_number)
                .first()
            )

            if existing_page:

                existing_page.image_url = image_url

                updated_pages += 1

                db.commit()

                db.refresh(existing_page)

                saved_pages.append({
                    "id": existing_page.id,
                    "chapter_id": existing_page.chapter_id,
                    "page_number": existing_page.page_number,
                    "image_url": existing_page.image_url
                })

            else:

                new_page = ChapterPage(
                    chapter_id=chapter.id,
                    page_number=page_number,
                    image_url=image_url
                )

                db.add(new_page)

                db.commit()

                db.refresh(new_page)

                created_pages += 1

                saved_pages.append({
                    "id": new_page.id,
                    "chapter_id": new_page.chapter_id,
                    "page_number": new_page.page_number,
                    "image_url": new_page.image_url
                })

        return {
            "success": True,
            "message": (
                f"Upload completo finalizado. "
                f"{created_pages} páginas criadas e {updated_pages} páginas atualizadas."
            ),
            "chapter": {
                "id": chapter.id,
                "number": chapter.number,
                "title": chapter.title
            },
            "total_files": len(validated_images),
            "created_pages": created_pages,
            "updated_pages": updated_pages,
            "pages": saved_pages
        }

    finally:

        db.close()

@app.delete("/admin/pages/{page_id}")
def admin_delete_chapter_page(page_id: int):

    db = SessionLocal()

    try:

        page = (
            db.query(ChapterPage)
            .filter(ChapterPage.id == page_id)
            .first()
        )

        if not page:

            return {
                "success": False,
                "message": "Página não encontrada"
            }

        db.delete(page)

        db.commit()

        return {
            "success": True,
            "message": "Página removida com sucesso"
        }

    finally:

        db.close()

# =========================================
# CADASTRAR USUÁRIO
# =========================================

@app.post("/users")
def create_user(user: UserCreate):

    db = SessionLocal()

    try:

        existing_user = (
            db.query(User)
            .filter(User.email == user.email)
            .first()
        )

        if existing_user:

            return {
                "success": False,
                "message": "E-mail já cadastrado"
            }
        default_avatar = (
            db.query(AvatarItem)
            .filter(AvatarItem.source_type == "initial")
            .filter(AvatarItem.name == "Avatar Padrão")
            .first()
        )

        new_user = User(

            nome=user.nome,

            apelido=user.apelido,

            email=user.email,

            telefone=user.telefone,

            senha=user.senha,

            receber_notificacoes=True,

            is_blocked=False,

            avatar_id=default_avatar.id if default_avatar else None,

            avatar_url=(
                default_avatar.image_url
                if default_avatar
                else "assets/avatars/default-avatar.png"
            )
        )

        db.add(new_user)

        db.commit()

        db.refresh(new_user)

        first_unlock = UserUnlock(

            user_id=new_user.id,

            unlock_type="chapter",

            unlock_key="cap1"
        )

        db.add(first_unlock)

        if default_avatar:
            first_avatar_unlock = UserAvatarUnlock(
                user_id=new_user.id,
                avatar_id=default_avatar.id
            )

            db.add(first_avatar_unlock)

        db.commit()

        return {
            "success": True,
            "message": "Usuário cadastrado com sucesso",
            "id": new_user.id
        }

    finally:

        db.close()

# =========================================
# LOGIN
# =========================================

@app.post("/login")
def login(data: LoginRequest):

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(User.email == data.email)
            .first()
        )

        if not user:

            return {
                "success": False,
                "message": "Usuário não encontrado"
            }

        if user.senha != data.senha:

            return {
                "success": False,
                "message": "Senha inválida"
            }

        if user.is_blocked:

            return {
                "success": False,
                "message": "Usuário bloqueado. Entre em contato com o suporte."
            }

        existing_unlock = (
            db.query(UserUnlock)
            .filter(UserUnlock.user_id == user.id)
            .filter(UserUnlock.unlock_type == "chapter")
            .filter(UserUnlock.unlock_key == "cap1")
            .first()
        )

        if not existing_unlock:

            first_unlock = UserUnlock(

                user_id=user.id,

                unlock_type="chapter",

                unlock_key="cap1"
            )

            db.add(first_unlock)

        default_avatar = (
            db.query(AvatarItem)
            .filter(AvatarItem.source_type == "initial")
            .filter(AvatarItem.name == "Avatar Padrão")
            .first()
        )

        if default_avatar:

            existing_avatar_unlock = (
                db.query(UserAvatarUnlock)
                .filter(UserAvatarUnlock.user_id == user.id)
                .filter(UserAvatarUnlock.avatar_id == default_avatar.id)
                .first()
            )

            if not existing_avatar_unlock:

                first_avatar_unlock = UserAvatarUnlock(
                    user_id=user.id,
                    avatar_id=default_avatar.id
                )

                db.add(first_avatar_unlock)

            if not user.avatar_id:

                user.avatar_id = default_avatar.id

            if not user.avatar_url:

                user.avatar_url = default_avatar.image_url

        if not user.avatar_url:

            user.avatar_url = "assets/avatars/default-avatar.png"

        db.commit()

        db.refresh(user)

        return {
            "success": True,
            "message": "Login realizado com sucesso",
            "user": {
                "id": user.id,
                "nome": user.nome,
                "apelido": user.apelido,
                "email": user.email,
                "telefone": user.telefone,
                "avatar_id": user.avatar_id,
                "avatar_url": user.avatar_url,
                "is_admin": check_is_admin(user.email),
                "is_blocked": user.is_blocked
            }
        }

    finally:

        db.close()

# =========================================
# RECUPERAÇÃO DE SENHA
# =========================================

@app.post("/password-recovery/request")
def create_password_recovery_request(data: PasswordRecoveryRequestCreate):

    db = SessionLocal()

    try:

        email = data.email.strip().lower()

        if not email:

            return {
                "success": False,
                "message": "Informe o e-mail cadastrado"
            }

        existing_pending_request = (
            db.query(PasswordRecoveryRequest)
            .filter(PasswordRecoveryRequest.email == email)
            .filter(PasswordRecoveryRequest.status == "pending")
            .first()
        )

        if existing_pending_request:

            return {
                "success": True,
                "message": "Já existe uma solicitação pendente para este e-mail"
            }

        new_request = PasswordRecoveryRequest(
            email=email,
            telefone=data.telefone,
            status="pending"
        )

        db.add(new_request)

        db.commit()

        db.refresh(new_request)

        return {
            "success": True,
            "message": "Solicitação de recuperação enviada com sucesso"
        }

    finally:

        db.close()


@app.get("/admin/password-recovery-requests")
def admin_get_password_recovery_requests():

    db = SessionLocal()

    try:

        requests = (
            db.query(PasswordRecoveryRequest)
            .order_by(PasswordRecoveryRequest.id.desc())
            .all()
        )

        return {
            "success": True,
            "requests": [
                {
                    "id": request.id,
                    "email": request.email,
                    "telefone": request.telefone,
                    "status": request.status,
                    "created_at": (
                        request.created_at.isoformat()
                        if request.created_at
                        else None
                    ),
                    "resolved_at": (
                        request.resolved_at.isoformat()
                        if request.resolved_at
                        else None
                    )
                }
                for request in requests
            ]
        }

    finally:

        db.close()


@app.put("/admin/password-recovery-requests/{request_id}/resolve")
def admin_resolve_password_recovery_request(
    request_id: int,
    data: PasswordRecoveryRequestResolve
):

    db = SessionLocal()

    try:

        recovery_request = (
            db.query(PasswordRecoveryRequest)
            .filter(PasswordRecoveryRequest.id == request_id)
            .first()
        )

        if not recovery_request:

            return {
                "success": False,
                "message": "Solicitação não encontrada"
            }

        recovery_request.status = data.status or "resolved"
        recovery_request.resolved_at = datetime.now()

        db.commit()

        return {
            "success": True,
            "message": "Solicitação marcada como resolvida"
        }

    finally:

        db.close()

# =========================================
# PERFIL DO USUÁRIO
# =========================================

@app.get("/users/{user_id}/profile")
def get_user_profile(user_id: int):

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(User.id == user_id)
            .first()
        )

        if not user:

            return {
                "success": False,
                "message": "Usuário não encontrado"
            }

        return {
            "success": True,
            "user": {
                "id": user.id,
                "nome": user.nome,
                "apelido": user.apelido,
                "email": user.email,
                "telefone": user.telefone,
                "avatar_id": user.avatar_id,
                "avatar_url": user.avatar_url,
                "receber_notificacoes": user.receber_notificacoes,
                "is_blocked": user.is_blocked,
                "is_admin": check_is_admin(user.email)
            }
        }

    finally:

        db.close()


@app.put("/users/{user_id}/profile")
def update_user_profile(user_id: int, data: UserProfileUpdate):

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(User.id == user_id)
            .first()
        )

        if not user:

            return {
                "success": False,
                "message": "Usuário não encontrado"
            }

        existing_email = (
            db.query(User)
            .filter(User.email == data.email)
            .filter(User.id != user_id)
            .first()
        )

        if existing_email:

            return {
                "success": False,
                "message": "Este e-mail já está sendo usado por outro usuário"
            }

        user.nome = data.nome
        user.apelido = data.apelido
        user.email = data.email
        user.telefone = data.telefone

        db.commit()

        db.refresh(user)

        return {
            "success": True,
            "message": "Perfil atualizado com sucesso",
            "user": {
                "id": user.id,
                "nome": user.nome,
                "apelido": user.apelido,
                "email": user.email,
                "telefone": user.telefone,
                "avatar_id": user.avatar_id,
                "avatar_url": user.avatar_url,
                "is_admin": check_is_admin(user.email),
                "is_blocked": user.is_blocked
            }
        }

    finally:

        db.close()


@app.put("/users/{user_id}/password")
def update_user_password(user_id: int, data: UserPasswordUpdate):

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(User.id == user_id)
            .first()
        )

        if not user:

            return {
                "success": False,
                "message": "Usuário não encontrado"
            }

        if user.senha != data.senha_atual:

            return {
                "success": False,
                "message": "Senha atual incorreta"
            }

        if data.nova_senha != data.confirmar_senha:

            return {
                "success": False,
                "message": "A nova senha e a confirmação não coincidem"
            }

        if len(data.nova_senha.strip()) < 6:

            return {
                "success": False,
                "message": "A nova senha precisa ter pelo menos 6 caracteres"
            }

        user.senha = data.nova_senha

        db.commit()

        return {
            "success": True,
            "message": "Senha alterada com sucesso"
        }

    finally:

        db.close()

# =========================================
# AVATARES DO USUÁRIO
# =========================================

@app.get("/users/{user_id}/avatars")
def get_user_avatars(user_id: int):

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(User.id == user_id)
            .first()
        )

        if not user:

            return {
                "success": False,
                "message": "Usuário não encontrado"
            }

        avatars = (
            db.query(AvatarItem)
            .filter(AvatarItem.is_active == True)
            .order_by(AvatarItem.id)
            .all()
        )

        unlocked_avatar_ids = [
            unlock.avatar_id
            for unlock in (
                db.query(UserAvatarUnlock)
                .filter(UserAvatarUnlock.user_id == user_id)
                .all()
            )
        ]

        return {
            "success": True,
            "avatars": [
                {
                    "id": avatar.id,
                    "name": avatar.name,
                    "description": avatar.description,
                    "image_url": avatar.image_url,
                    "rarity": avatar.rarity,
                    "source_type": avatar.source_type,
                    "unlock_type": avatar.unlock_type,
                    "unlock_key": avatar.unlock_key,
                    "price": avatar.price,
                    "is_active": avatar.is_active,
                    "is_unlocked": avatar.id in unlocked_avatar_ids,
                    "is_selected": avatar.id == user.avatar_id
                }
                for avatar in avatars
            ]
        }

    finally:

        db.close()


@app.put("/users/{user_id}/avatar")
def select_user_avatar(user_id: int, data: UserAvatarSelect):

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(User.id == user_id)
            .first()
        )

        if not user:

            return {
                "success": False,
                "message": "Usuário não encontrado"
            }

        avatar = (
            db.query(AvatarItem)
            .filter(AvatarItem.id == data.avatar_id)
            .filter(AvatarItem.is_active == True)
            .first()
        )

        if not avatar:

            return {
                "success": False,
                "message": "Avatar não encontrado ou indisponível"
            }

        unlocked_avatar = (
            db.query(UserAvatarUnlock)
            .filter(UserAvatarUnlock.user_id == user_id)
            .filter(UserAvatarUnlock.avatar_id == avatar.id)
            .first()
        )

        if not unlocked_avatar:

            return {
                "success": False,
                "message": "Este avatar ainda não foi desbloqueado"
            }

        user.avatar_id = avatar.id
        user.avatar_url = avatar.image_url

        db.commit()

        db.refresh(user)

        return {
            "success": True,
            "message": "Avatar atualizado com sucesso",
            "user": {
                "id": user.id,
                "nome": user.nome,
                "apelido": user.apelido,
                "email": user.email,
                "telefone": user.telefone,
                "avatar_id": user.avatar_id,
                "avatar_url": user.avatar_url,
                "is_admin": check_is_admin(user.email),
                "is_blocked": user.is_blocked
            }
        }


    finally:

        db.close()

    # =========================================
    # ADMIN - GERENCIAR AVATARES
    # =========================================


@app.get("/admin/avatars")
def admin_get_avatars():
    db = SessionLocal()

    try:

        avatars = (
            db.query(AvatarItem)
            .order_by(AvatarItem.id)
            .all()
        )

        return {
            "success": True,
            "avatars": [
                {
                    "id": avatar.id,
                    "name": avatar.name,
                    "description": avatar.description,
                    "image_url": avatar.image_url,
                    "rarity": avatar.rarity,
                    "source_type": avatar.source_type,
                    "unlock_type": avatar.unlock_type,
                    "unlock_key": avatar.unlock_key,
                    "price": avatar.price,
                    "is_active": avatar.is_active
                }
                for avatar in avatars
            ]
        }

    finally:

        db.close()


@app.post("/admin/avatars")
def admin_create_avatar(data: AvatarItemCreate):
    db = SessionLocal()

    try:

        new_avatar = AvatarItem(
            name=data.name,
            description=data.description,
            image_url=data.image_url,
            rarity=data.rarity,
            source_type=data.source_type,
            unlock_type=data.unlock_type,
            unlock_key=data.unlock_key,
            price=data.price,
            is_active=data.is_active
        )

        db.add(new_avatar)

        db.commit()

        db.refresh(new_avatar)

        return {
            "success": True,
            "message": "Avatar criado com sucesso",
            "avatar": {
                "id": new_avatar.id,
                "name": new_avatar.name,
                "description": new_avatar.description,
                "image_url": new_avatar.image_url,
                "rarity": new_avatar.rarity,
                "source_type": new_avatar.source_type,
                "unlock_type": new_avatar.unlock_type,
                "unlock_key": new_avatar.unlock_key,
                "price": new_avatar.price,
                "is_active": new_avatar.is_active
            }
        }

    finally:

        db.close()


@app.put("/admin/avatars/{avatar_id}")
def admin_update_avatar(avatar_id: int, data: AvatarItemUpdate):
    db = SessionLocal()

    try:

        avatar = (
            db.query(AvatarItem)
            .filter(AvatarItem.id == avatar_id)
            .first()
        )

        if not avatar:
            return {
                "success": False,
                "message": "Avatar não encontrado"
            }

        if data.name is not None:
            avatar.name = data.name

        if data.description is not None:
            avatar.description = data.description

        if data.image_url is not None:
            avatar.image_url = data.image_url

        if data.rarity is not None:
            avatar.rarity = data.rarity

        if data.source_type is not None:
            avatar.source_type = data.source_type

        if data.unlock_type is not None:
            avatar.unlock_type = data.unlock_type

        if data.unlock_key is not None:
            avatar.unlock_key = data.unlock_key

        if data.price is not None:
            avatar.price = data.price

        if data.is_active is not None:
            avatar.is_active = data.is_active

        db.commit()

        db.refresh(avatar)

        return {
            "success": True,
            "message": "Avatar atualizado com sucesso",
            "avatar": {
                "id": avatar.id,
                "name": avatar.name,
                "description": avatar.description,
                "image_url": avatar.image_url,
                "rarity": avatar.rarity,
                "source_type": avatar.source_type,
                "unlock_type": avatar.unlock_type,
                "unlock_key": avatar.unlock_key,
                "price": avatar.price,
                "is_active": avatar.is_active
            }
        }

    finally:

        db.close()


@app.delete("/admin/avatars/{avatar_id}")
def admin_delete_avatar(avatar_id: int):
    db = SessionLocal()

    try:

        avatar = (
            db.query(AvatarItem)
            .filter(AvatarItem.id == avatar_id)
            .first()
        )

        if not avatar:
            return {
                "success": False,
                "message": "Avatar não encontrado"
            }

        if avatar.source_type == "initial":
            return {
                "success": False,
                "message": "Não é permitido excluir o avatar padrão inicial"
            }

        users_using_avatar = (
            db.query(User)
            .filter(User.avatar_id == avatar.id)
            .first()
        )

        if users_using_avatar:
            return {
                "success": False,
                "message": "Não é possível excluir um avatar que está em uso por usuários"
            }

        (
            db.query(UserAvatarUnlock)
            .filter(UserAvatarUnlock.avatar_id == avatar.id)
            .delete()
        )

        db.delete(avatar)

        db.commit()

        return {
            "success": True,
            "message": "Avatar removido com sucesso"
        }

    finally:

        db.close()

@app.post("/admin/avatars/{avatar_id}/upload")
async def admin_upload_avatar_image(
    avatar_id: int,
    image: UploadFile = File(...)
):

    db = SessionLocal()

    try:

        avatar = (
            db.query(AvatarItem)
            .filter(AvatarItem.id == avatar_id)
            .first()
        )

        if not avatar:

            return {
                "success": False,
                "message": "Avatar não encontrado"
            }

        allowed_extensions = [".jpg", ".jpeg", ".png", ".webp"]

        file_extension = os.path.splitext(image.filename)[1].lower()

        if file_extension not in allowed_extensions:

            return {
                "success": False,
                "message": "Formato inválido. Use JPG, JPEG, PNG ou WEBP."
            }

        avatar_folder = "manga/avatars"

        os.makedirs(avatar_folder, exist_ok=True)

        timestamp = int(time.time())

        file_name = f"avatar-{avatar.id}-{timestamp}{file_extension}"

        file_path = os.path.join(avatar_folder, file_name)

        with open(file_path, "wb") as buffer:

            shutil.copyfileobj(image.file, buffer)

            image_url = f"/manga/avatars/{file_name}"

        avatar.image_url = image_url

        db.commit()

        db.refresh(avatar)

        return {
            "success": True,
            "message": "Imagem do avatar enviada com sucesso",
            "avatar": {
                "id": avatar.id,
                "name": avatar.name,
                "description": avatar.description,
                "image_url": avatar.image_url,
                "rarity": avatar.rarity,
                "source_type": avatar.source_type,
                "unlock_type": avatar.unlock_type,
                "unlock_key": avatar.unlock_key,
                "price": avatar.price,
                "is_active": avatar.is_active
            }
        }

    finally:

        db.close()


# =========================================
# ADMIN - GERENCIAR AVATARES DOS USUÁRIOS
# =========================================

@app.post("/admin/users/{user_id}/avatars/{avatar_id}/unlock")
def admin_unlock_avatar_for_user(user_id: int, avatar_id: int):

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(User.id == user_id)
            .first()
        )

        if not user:

            return {
                "success": False,
                "message": "Usuário não encontrado"
            }

        avatar = (
            db.query(AvatarItem)
            .filter(AvatarItem.id == avatar_id)
            .filter(AvatarItem.is_active == True)
            .first()
        )

        if not avatar:

            return {
                "success": False,
                "message": "Avatar não encontrado ou inativo"
            }

        existing_unlock = (
            db.query(UserAvatarUnlock)
            .filter(UserAvatarUnlock.user_id == user.id)
            .filter(UserAvatarUnlock.avatar_id == avatar.id)
            .first()
        )

        if existing_unlock:

            return {
                "success": False,
                "message": "Este usuário já possui esse avatar"
            }

        new_unlock = UserAvatarUnlock(
            user_id=user.id,
            avatar_id=avatar.id
        )

        db.add(new_unlock)

        db.commit()

        db.refresh(new_unlock)

        return {
            "success": True,
            "message": "Avatar liberado para o usuário com sucesso",
            "unlock": {
                "id": new_unlock.id,
                "user_id": new_unlock.user_id,
                "avatar_id": new_unlock.avatar_id
            }
        }

    finally:

        db.close()


@app.delete("/admin/users/{user_id}/avatars/{avatar_id}/unlock")
def admin_remove_avatar_from_user(user_id: int, avatar_id: int):

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(User.id == user_id)
            .first()
        )

        if not user:

            return {
                "success": False,
                "message": "Usuário não encontrado"
            }

        avatar_unlock = (
            db.query(UserAvatarUnlock)
            .filter(UserAvatarUnlock.user_id == user.id)
            .filter(UserAvatarUnlock.avatar_id == avatar_id)
            .first()
        )

        if not avatar_unlock:

            return {
                "success": False,
                "message": "Este usuário não possui esse avatar"
            }

        default_avatar = (
            db.query(AvatarItem)
            .filter(AvatarItem.source_type == "initial")
            .filter(AvatarItem.name == "Avatar Padrão")
            .first()
        )

        if user.avatar_id == avatar_id:

            if default_avatar:

                user.avatar_id = default_avatar.id
                user.avatar_url = default_avatar.image_url

            else:

                user.avatar_id = None
                user.avatar_url = "assets/avatars/default-avatar.png"

        db.delete(avatar_unlock)

        db.commit()

        return {
            "success": True,
            "message": "Avatar removido do usuário com sucesso"
        }

    finally:

        db.close()

        @app.post("/admin/users/{user_id}/avatars/{avatar_id}/unlock")
        def admin_unlock_avatar_for_user(user_id: int, avatar_id: int):

            db = SessionLocal()

            try:

                user = (
                    db.query(User)
                    .filter(User.id == user_id)
                    .first()
                )

                if not user:
                    return {
                        "success": False,
                        "message": "Usuário não encontrado"
                    }

                avatar = (
                    db.query(AvatarItem)
                    .filter(AvatarItem.id == avatar_id)
                    .filter(AvatarItem.is_active == True)
                    .first()
                )

                if not avatar:
                    return {
                        "success": False,
                        "message": "Avatar não encontrado ou inativo"
                    }

                existing_unlock = (
                    db.query(UserAvatarUnlock)
                    .filter(UserAvatarUnlock.user_id == user.id)
                    .filter(UserAvatarUnlock.avatar_id == avatar.id)
                    .first()
                )

                if existing_unlock:
                    return {
                        "success": False,
                        "message": "Este usuário já possui esse avatar"
                    }

                new_unlock = UserAvatarUnlock(
                    user_id=user.id,
                    avatar_id=avatar.id
                )

                db.add(new_unlock)

                db.commit()

                db.refresh(new_unlock)

                return {
                    "success": True,
                    "message": "Avatar liberado para o usuário com sucesso",
                    "unlock": {
                        "id": new_unlock.id,
                        "user_id": new_unlock.user_id,
                        "avatar_id": new_unlock.avatar_id
                    }
                }

            finally:

                db.close()

@app.delete("/admin/users/{user_id}/avatars/{avatar_id}/unlock")
def admin_remove_avatar_from_user(user_id: int, avatar_id: int):

            db = SessionLocal()

            try:

                user = (
                    db.query(User)
                    .filter(User.id == user_id)
                    .first()
                )

                if not user:
                    return {
                        "success": False,
                        "message": "Usuário não encontrado"
                    }

                avatar_unlock = (
                    db.query(UserAvatarUnlock)
                    .filter(UserAvatarUnlock.user_id == user.id)
                    .filter(UserAvatarUnlock.avatar_id == avatar_id)
                    .first()
                )

                if not avatar_unlock:
                    return {
                        "success": False,
                        "message": "Este usuário não possui esse avatar"
                    }

                default_avatar = (
                    db.query(AvatarItem)
                    .filter(AvatarItem.source_type == "initial")
                    .filter(AvatarItem.name == "Avatar Padrão")
                    .first()
                )

                if user.avatar_id == avatar_id:

                    if default_avatar:

                        user.avatar_id = default_avatar.id
                        user.avatar_url = default_avatar.image_url

                    else:

                        user.avatar_id = None
                        user.avatar_url = "assets/avatars/default-avatar.png"

                db.delete(avatar_unlock)

                db.commit()

                return {
                    "success": True,
                    "message": "Avatar removido do usuário com sucesso"
                }

            finally:

                db.close()
# =========================================
# TRAJES DO USUÁRIO
# =========================================

@app.get("/users/{user_id}/outfits")
def get_user_outfits(user_id: int):

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(User.id == user_id)
            .first()
        )

        if not user:

            return {
                "success": False,
                "message": "Usuário não encontrado"
            }

        outfits = (
            db.query(OutfitItem)
            .filter(OutfitItem.is_active == True)
            .order_by(OutfitItem.id)
            .all()
        )

        user_outfit_unlocks = (
            db.query(UserOutfitUnlock)
            .filter(UserOutfitUnlock.user_id == user.id)
            .all()
        )

        unlocked_outfit_ids = [
            unlock.outfit_id
            for unlock in user_outfit_unlocks
        ]

        equipped_outfit_ids = [
            unlock.outfit_id
            for unlock in user_outfit_unlocks
            if unlock.is_equipped
        ]

        return {
            "success": True,
            "outfits": [
                {
                    "id": outfit.id,
                    "name": outfit.name,
                    "description": outfit.description,
                    "image_url": outfit.image_url,
                    "rarity": outfit.rarity,
                    "outfit_type": outfit.outfit_type,
                    "source_type": outfit.source_type,
                    "unlock_type": outfit.unlock_type,
                    "unlock_key": outfit.unlock_key,
                    "price": outfit.price,
                    "is_active": outfit.is_active,
                    "is_unlocked": outfit.id in unlocked_outfit_ids,
                    "is_equipped": outfit.id in equipped_outfit_ids
                }
                for outfit in outfits
            ]
        }

    finally:

        db.close()


@app.put("/users/{user_id}/outfit")
def select_user_outfit(user_id: int, data: UserOutfitSelect):

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(User.id == user_id)
            .first()
        )

        if not user:

            return {
                "success": False,
                "message": "Usuário não encontrado"
            }

        outfit = (
            db.query(OutfitItem)
            .filter(OutfitItem.id == data.outfit_id)
            .filter(OutfitItem.is_active == True)
            .first()
        )

        if not outfit:

            return {
                "success": False,
                "message": "Traje não encontrado ou indisponível"
            }

        unlocked_outfit = (
            db.query(UserOutfitUnlock)
            .filter(UserOutfitUnlock.user_id == user.id)
            .filter(UserOutfitUnlock.outfit_id == outfit.id)
            .first()
        )

        if not unlocked_outfit:

            return {
                "success": False,
                "message": "Este traje ainda não foi desbloqueado"
            }

        (
            db.query(UserOutfitUnlock)
            .filter(UserOutfitUnlock.user_id == user.id)
            .update({
                "is_equipped": False
            })
        )

        unlocked_outfit.is_equipped = True

        db.commit()

        db.refresh(unlocked_outfit)

        return {
            "success": True,
            "message": "Traje equipado com sucesso",
            "outfit": {
                "id": outfit.id,
                "name": outfit.name,
                "description": outfit.description,
                "image_url": outfit.image_url,
                "rarity": outfit.rarity,
                "outfit_type": outfit.outfit_type,
                "is_equipped": unlocked_outfit.is_equipped
            }
        }

    finally:

        db.close()


@app.post("/users/{user_id}/chapters/{chapter_number}/finish")
def finish_chapter_and_unlock_rewards(user_id: int, chapter_number: int):

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(User.id == user_id)
            .first()
        )

        if not user:

            return {
                "success": False,
                "message": "Usuário não encontrado"
            }

        unlock_key = f"cap{chapter_number}"

        reward_outfits = (
            db.query(OutfitItem)
            .filter(OutfitItem.is_active == True)
            .filter(OutfitItem.unlock_type == "chapter_finish")
            .filter(OutfitItem.unlock_key == unlock_key)
            .all()
        )

        reward_avatars = (
            db.query(AvatarItem)
            .filter(AvatarItem.is_active == True)
            .filter(AvatarItem.unlock_type == "chapter_finish")
            .filter(AvatarItem.unlock_key == unlock_key)
            .all()
        )

        unlocked_outfits = []

        unlocked_avatars = []

        for outfit in reward_outfits:

            existing_outfit_unlock = (
                db.query(UserOutfitUnlock)
                .filter(UserOutfitUnlock.user_id == user.id)
                .filter(UserOutfitUnlock.outfit_id == outfit.id)
                .first()
            )

            if existing_outfit_unlock:
                continue

            new_outfit_unlock = UserOutfitUnlock(
                user_id=user.id,
                outfit_id=outfit.id,
                is_equipped=False
            )

            db.add(new_outfit_unlock)

            unlocked_outfits.append({
                "id": outfit.id,
                "name": outfit.name,
                "description": outfit.description,
                "image_url": outfit.image_url,
                "rarity": outfit.rarity,
                "outfit_type": outfit.outfit_type
            })

        for avatar in reward_avatars:

            existing_avatar_unlock = (
                db.query(UserAvatarUnlock)
                .filter(UserAvatarUnlock.user_id == user.id)
                .filter(UserAvatarUnlock.avatar_id == avatar.id)
                .first()
            )

            if existing_avatar_unlock:
                continue

            new_avatar_unlock = UserAvatarUnlock(
                user_id=user.id,
                avatar_id=avatar.id
            )

            db.add(new_avatar_unlock)

            unlocked_avatars.append({
                "id": avatar.id,
                "name": avatar.name,
                "description": avatar.description,
                "image_url": avatar.image_url,
                "rarity": avatar.rarity,
                "source_type": avatar.source_type,
                "unlock_type": avatar.unlock_type,
                "unlock_key": avatar.unlock_key
            })

        db.commit()

        return {
            "success": True,
            "message": "Capítulo finalizado e recompensas verificadas",
            "chapter": chapter_number,
            "unlocked_outfits": unlocked_outfits,
            "unlocked_avatars": unlocked_avatars
        }

    finally:

        db.close()
# =========================================
# ADMIN - GERENCIAR USUÁRIOS
# =========================================

@app.get("/admin/users")
def admin_get_users():

    db = SessionLocal()

    try:

        users = (
            db.query(User)
            .order_by(User.id)
            .all()
        )

        return {
            "success": True,
            "users": [
                {
                    "id": user.id,
                    "nome": user.nome,
                    "apelido": user.apelido,
                    "email": user.email,
                    "telefone": user.telefone,
                    "receber_notificacoes": user.receber_notificacoes,
                    "is_blocked": user.is_blocked,
                    "is_admin": check_is_admin(user.email)
                }
                for user in users
            ]
        }

    finally:

        db.close()


@app.put("/admin/users/{user_id}/block")
def admin_block_user(user_id: int):

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(User.id == user_id)
            .first()
        )

        if not user:

            return {
                "success": False,
                "message": "Usuário não encontrado"
            }

        if check_is_admin(user.email):

            return {
                "success": False,
                "message": "Não é permitido bloquear o administrador principal"
            }

        user.is_blocked = True

        db.commit()

        db.refresh(user)

        return {
            "success": True,
            "message": "Usuário bloqueado com sucesso",
            "user": {
                "id": user.id,
                "nome": user.nome,
                "apelido": user.apelido,
                "email": user.email,
                "telefone": user.telefone,
                "is_blocked": user.is_blocked,
                "is_admin": check_is_admin(user.email)
            }
        }

    finally:

        db.close()


@app.put("/admin/users/{user_id}/unblock")
def admin_unblock_user(user_id: int):

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(User.id == user_id)
            .first()
        )

        if not user:

            return {
                "success": False,
                "message": "Usuário não encontrado"
            }

        user.is_blocked = False

        db.commit()

        db.refresh(user)

        return {
            "success": True,
            "message": "Usuário desbloqueado com sucesso",
            "user": {
                "id": user.id,
                "nome": user.nome,
                "apelido": user.apelido,
                "email": user.email,
                "telefone": user.telefone,
                "is_blocked": user.is_blocked,
                "is_admin": check_is_admin(user.email)
            }
        }

    finally:

        db.close()
@app.put("/admin/users/{user_id}/reset-password")
def admin_reset_user_password(user_id: int, data: AdminPasswordReset):

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(User.id == user_id)
            .first()
        )

        if not user:

            return {
                "success": False,
                "message": "Usuário não encontrado"
            }

        if check_is_admin(user.email):

            return {
                "success": False,
                "message": "Não é permitido resetar a senha do administrador principal"
            }

        if data.nova_senha != data.confirmar_senha:

            return {
                "success": False,
                "message": "A nova senha e a confirmação não coincidem"
            }

        if len(data.nova_senha.strip()) < 6:

            return {
                "success": False,
                "message": "A nova senha precisa ter pelo menos 6 caracteres"
            }

        user.senha = data.nova_senha.strip()

        db.commit()

        return {
            "success": True,
            "message": "Senha do usuário resetada com sucesso"
        }

    finally:

        db.close()

@app.delete("/admin/users/{user_id}")
def admin_delete_user(user_id: int):

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(User.id == user_id)
            .first()
        )

        if not user:

            return {
                "success": False,
                "message": "Usuário não encontrado"
            }

        if check_is_admin(user.email):

            return {
                "success": False,
                "message": "Não é permitido excluir o administrador principal"
            }

        (
            db.query(ReadingProgress)
            .filter(ReadingProgress.user_id == user.id)
            .delete()
        )

        (
            db.query(UserUnlock)
            .filter(UserUnlock.user_id == user.id)
            .delete()
        )

        (
            db.query(UserAvatarUnlock)
            .filter(UserAvatarUnlock.user_id == user.id)
            .delete()
        )

        (
            db.query(UserOutfitUnlock)
            .filter(UserOutfitUnlock.user_id == user.id)
            .delete()
        )

        db.delete(user)

        db.commit()

        return {
            "success": True,
            "message": "Usuário excluído permanentemente com sucesso"
        }

    finally:

        db.close()

# =========================================
# LISTAR USUÁRIOS
# =========================================

@app.get("/users")
def get_users():

    db = SessionLocal()

    try:

        users = db.query(User).all()

        return users

    finally:

        db.close()

# =========================================
# SALVAR PROGRESSO DE LEITURA
# =========================================

@app.post("/reading-progress")
def save_reading_progress(progress: ReadingProgressCreate):

    db = SessionLocal()

    try:

        existing_progress = (
            db.query(ReadingProgress)
            .filter(ReadingProgress.user_id == progress.user_id)
            .first()
        )

        if existing_progress:

            existing_progress.chapter = progress.chapter

            existing_progress.page = progress.page

            db.commit()

            db.refresh(existing_progress)

            return {
                "success": True,
                "message": "Progresso atualizado com sucesso",
                "progress": {
                    "user_id": existing_progress.user_id,
                    "chapter": existing_progress.chapter,
                    "page": existing_progress.page
                }
            }

        new_progress = ReadingProgress(

            user_id=progress.user_id,

            chapter=progress.chapter,

            page=progress.page
        )

        db.add(new_progress)

        db.commit()

        db.refresh(new_progress)

        return {
            "success": True,
            "message": "Progresso salvo com sucesso",
            "progress": {
                "user_id": new_progress.user_id,
                "chapter": new_progress.chapter,
                "page": new_progress.page
            }
        }

    finally:

        db.close()

# =========================================
# BUSCAR PROGRESSO DE LEITURA
# =========================================

@app.get("/reading-progress/{user_id}")
def get_reading_progress(user_id: int):

    db = SessionLocal()

    try:

        progress = (
            db.query(ReadingProgress)
            .filter(ReadingProgress.user_id == user_id)
            .first()
        )

        if not progress:

            return {
                "success": False,
                "message": "Nenhum progresso encontrado"
            }

        return {
            "success": True,
            "progress": {
                "user_id": progress.user_id,
                "chapter": progress.chapter,
                "page": progress.page
            }
        }

    finally:

        db.close()

# =========================================
# CRIAR DESBLOQUEIO
# =========================================

@app.post("/unlocks")
def create_unlock(unlock: UserUnlockCreate):

    db = SessionLocal()

    try:

        existing_unlock = (
            db.query(UserUnlock)
            .filter(UserUnlock.user_id == unlock.user_id)
            .filter(UserUnlock.unlock_type == unlock.unlock_type)
            .filter(UserUnlock.unlock_key == unlock.unlock_key)
            .first()
        )

        if existing_unlock:

            return {
                "success": False,
                "message": "Desbloqueio já existe"
            }

        new_unlock = UserUnlock(

            user_id=unlock.user_id,

            unlock_type=unlock.unlock_type,

            unlock_key=unlock.unlock_key
        )

        db.add(new_unlock)

        db.commit()

        db.refresh(new_unlock)

        return {
            "success": True,
            "message": "Desbloqueio criado com sucesso",
            "unlock": {
                "user_id": new_unlock.user_id,
                "unlock_type": new_unlock.unlock_type,
                "unlock_key": new_unlock.unlock_key
            }
        }

    finally:

        db.close()

# =========================================
# BUSCAR DESBLOQUEIOS DO USUÁRIO
# =========================================

@app.get("/unlocks/{user_id}")
def get_user_unlocks(user_id: int):

    db = SessionLocal()

    try:

        unlocks = (
            db.query(UserUnlock)
            .filter(UserUnlock.user_id == user_id)
            .all()
        )

        return {
            "success": True,
            "unlocks": [
                {
                    "unlock_type": unlock.unlock_type,
                    "unlock_key": unlock.unlock_key
                }
                for unlock in unlocks
            ]
        }

    finally:

        db.close()
