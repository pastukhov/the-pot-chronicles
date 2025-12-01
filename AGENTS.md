# Repository Guidelines

## Project Structure & Module Organization
- `scripts/` — automation: `fetch_chats.py`, `extract_recipes.py`, `generate_images.py`, `rebuild_menu.py`.
- `raw_threads/` — загруженные треды из OpenAI Threads API (JSON).
- `recipes/` — Markdown-рецепты с фронтматтером; `images/` — иллюстрации.
- `site/` — Hugo сайт, монтирует рецепты и картинки; `site/config.yaml` главный конфиг.
- `.github/workflows/` — CI: обновление данных и деплой на GitHub Pages.

## Build, Test, and Development Commands
- `pip install -r scripts/requirements.txt` — установка зависимостей.
- `python scripts/fetch_chats.py` — скачать треды в `raw_threads/`.
- `python scripts/extract_recipes.py` — извлечь рецепты в `recipes/`.
- `python scripts/generate_images.py` — сгенерировать иллюстрации для рецептов без `image`.
- `python scripts/rebuild_menu.py` — обновить меню Hugo по категориям.
- `cd site && hugo server` — локальный превью сайта.

## Coding Style & Naming Conventions
- Индентация 2 пробела; UTF-8; LF.
- Python: следовать PEP 8, минимальные импорты; избегать магических значений.
- YAML/Markdown: двойные кавычки по необходимости, без лишних пробелов; пути в UNIX-стиле.
- Имена файлов: нижний регистр, дефисы/подчеркивания (`config.yaml`, `generate_images.py`).

## Testing Guidelines
- Формального тестового контура нет; перед пушем прогоняйте ключевые скрипты локально, если есть `OPENAI_API_KEY`.
- Проверяйте идемпотентность: повторный запуск не должен создавать дубликаты.

## Commit & Pull Request Guidelines
- Коммиты короткие и предметные, желательно в повелительном наклонении (`docs: add agents guide`, `ci: rebuild menu`).
- PR: указывайте цель, основные изменения, шаги проверки, риски/ограничения; добавляйте ссылки на задачи/issue.

## Security & Configuration Tips
- Не коммитить реальные ключи/токены; используйте секреты GitHub (`OPENAI_API_KEY`, `GITHUB_TOKEN`).
- Папки `log/`, `sessions/`, `auth.json`, `history.jsonl` должны быть в `.gitignore`; не храните приватные данные в репозитории.
