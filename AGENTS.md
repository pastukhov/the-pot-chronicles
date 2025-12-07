# Repository Guidelines

## Project Structure & Module Organization
- `scripts/` — импорт и обработка: `import_conversations.py` (генерация рецептов из `export/conversations.json`), `translate_categories.py` (перевод тегов на русский), `generate_images.py`, `rebuild_menu.py`, `proofread_recipes.py`.
- `export/` — локальный дамп чатов ChatGPT; не пушить.
- `recipes/` — Markdown-рецепты с фронтматтером; `images/` — иллюстрации для них.
- `site/` — Hugo сайт (`config.yaml`, шаблоны и статическая страница архивов), обрабатывает рецепты/картинки.
- `.github/workflows/` — деплой на GitHub Pages; импорт чатов отключен в CI.

## Build, Test, and Development Commands
- `./scripts/import_from_export.sh` — создать venv, установить зависимости, импортировать рецепты из `export/conversations.json`, перевести теги, сгенерировать картинки, обновить меню/архив.
- `source .venv/bin/activate && python scripts/generate_images.py` — догенерировать отсутствующие картинки.
- `python scripts/translate_categories.py` — одноразовый перевод существующих тегов на русский.
- `python scripts/proofread_recipes.py --apply` — вычитать/исправить рецепты через OpenAI (требует `OPENAI_API_KEY`).
- `cd site && hugo server` — локальный превью. Hugo нужен локально.

## Coding Style & Naming Conventions
- Индентация 2 пробела; UTF-8; LF.
- Python: PEP 8, явные константы, идемпотентные скрипты (повторный запуск не должен плодить дубликаты).
- YAML/Markdown: двойные кавычки по необходимости, без лишних пробелов; пути в UNIX-стиле.
- Имена файлов: нижний регистр, дефисы (`site/config.yaml`, `import_conversations.py`).

## Testing Guidelines
- Формального тестового контура нет. Перед пушем прогоняйте ключевые скрипты локально (с venv), если нужен `OPENAI_API_KEY`.
- Проверяйте идемпотентность: скрипты импорта и генерации картинок не должны переписывать существующие артефакты без причины.

## Commit & Pull Request Guidelines
- Коммиты короткие и предметные, желательно в повелительном наклонении (`docs: add agents guide`, `ci: rebuild menu`).
- PR: цель, изменения, шаги проверки, риски/ограничения; ссылки на задачи/issue.

## Security & Configuration Tips
- Не коммитить реальные ключи/токены. Локальный `OPENAI_API_KEY` хранить в `.env` (не пушить); CI использует секреты GitHub.
- Импорт из ассистента через API выключен в CI; основной ввод — локальный `export/conversations.json`.
- `log/`, `sessions/`, `auth.json`, `history.jsonl` и другие чувствительные артефакты — в `.gitignore`; не хранить приватные данные в репо.
