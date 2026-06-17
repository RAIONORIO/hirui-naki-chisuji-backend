import re
from pathlib import Path

from database import Base, engine, SessionLocal
from models import Chapter, ChapterPage


MANGA_DIR = Path("manga")
COVERS_DIR = MANGA_DIR / "covers"

VALID_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


CHAPTER_TITLES = {
    0: "Fragmento Oculto",
    1: "Capítulo 1",
    2: "Capítulo 2",
    3: "Capítulo 3",
    4: "Capítulo 4",
    5: "Capítulo 5",
}


def get_chapter_number(folder_name: str):
    match = re.fullmatch(r"cap(\d+)", folder_name.lower())

    if not match:
        return None

    return int(match.group(1))


def get_sorted_image_files(chapter_folder: Path):
    image_files = []

    for file_path in chapter_folder.iterdir():
        if not file_path.is_file():
            continue

        if file_path.suffix.lower() not in VALID_IMAGE_EXTENSIONS:
            continue

        page_number_text = file_path.stem

        if not page_number_text.isdigit():
            continue

        image_files.append((int(page_number_text), file_path))

    image_files.sort(key=lambda item: item[0])

    return image_files


def find_cover_for_chapter(chapter_number: int):
    if not COVERS_DIR.exists():
        return None

    possible_names = [
        f"cap{chapter_number}",
        f"capitulo{chapter_number}",
        f"chapter{chapter_number}",
        f"chapter-{chapter_number}",
        f"chapter_{chapter_number}",
    ]

    for file_path in COVERS_DIR.iterdir():
        if not file_path.is_file():
            continue

        if file_path.suffix.lower() not in VALID_IMAGE_EXTENSIONS:
            continue

        file_name_lower = file_path.stem.lower()

        if any(name in file_name_lower for name in possible_names):
            return f"/manga/covers/{file_path.name}"

    return None


def seed_chapters():
    Base.metadata.create_all(bind=engine)

    if not MANGA_DIR.exists():
        print("Pasta manga/ não encontrada.")
        return

    db = SessionLocal()

    try:
        chapter_folders = []

        for folder in MANGA_DIR.iterdir():
            if not folder.is_dir():
                continue

            chapter_number = get_chapter_number(folder.name)

            if chapter_number is None:
                continue

            chapter_folders.append((chapter_number, folder))

        chapter_folders.sort(key=lambda item: item[0])

        if not chapter_folders:
            print("Nenhuma pasta capN encontrada dentro de manga/.")
            return

        for chapter_number, chapter_folder in chapter_folders:
            image_files = get_sorted_image_files(chapter_folder)

            if not image_files:
                print(f"Capítulo {chapter_number}: nenhuma imagem válida encontrada.")
                continue

            chapter = (
                db.query(Chapter)
                .filter(Chapter.number == chapter_number)
                .first()
            )

            cover_image = find_cover_for_chapter(chapter_number)

            if not chapter:
                chapter = Chapter(
                    number=chapter_number,
                    title=CHAPTER_TITLES.get(
                        chapter_number,
                        f"Capítulo {chapter_number}"
                    ),
                    description="",
                    cover_image=cover_image,
                    release_date="",
                    is_published=True
                )

                db.add(chapter)
                db.commit()
                db.refresh(chapter)

                print(f"Capítulo {chapter_number}: criado.")

            else:
                if cover_image:
                    chapter.cover_image = cover_image

                chapter.title = chapter.title or CHAPTER_TITLES.get(
                    chapter_number,
                    f"Capítulo {chapter_number}"
                )

                chapter.description = chapter.description or ""
                chapter.release_date = chapter.release_date or ""
                chapter.is_published = True

                db.commit()
                db.refresh(chapter)

                print(f"Capítulo {chapter_number}: atualizado.")

            created_pages = 0
            updated_pages = 0

            for page_number, image_path in image_files:
                image_url = f"/manga/{chapter_folder.name}/{image_path.name}"

                existing_page = (
                    db.query(ChapterPage)
                    .filter(ChapterPage.chapter_id == chapter.id)
                    .filter(ChapterPage.page_number == page_number)
                    .first()
                )

                if existing_page:
                    existing_page.image_url = image_url
                    updated_pages += 1

                else:
                    new_page = ChapterPage(
                        chapter_id=chapter.id,
                        page_number=page_number,
                        image_url=image_url
                    )

                    db.add(new_page)
                    created_pages += 1

            db.commit()

            print(
                f"Capítulo {chapter_number}: "
                f"{created_pages} páginas criadas, "
                f"{updated_pages} páginas atualizadas."
            )

        print("Seed de capítulos finalizado.")

    finally:
        db.close()


if __name__ == "__main__":
    seed_chapters()