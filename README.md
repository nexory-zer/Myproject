# Study Tracker

Веб-приложение на Flask для учёта учебных целей и занятий. Логика прежнего Telegram-бота сохранена: цели, статистика, история по дате, добавление и редактирование занятий, сброс статистики.

## Запуск

```powershell
python -m venv .venv
.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
python bot.py
```

Откройте http://127.0.0.1:5000. Данные хранятся в `study_bot.db`.
