# AGENTS.md — инструкции для Codex и AI-агентов

## Правило обработки ошибок (глобальное)

Если любая выполненная команда вернула ненулевой код завершения — немедленно активируй скилл `error-recovery` и следуй его циклу. Задачу нельзя считать выполненной, пока упавшая команда не завершится успешно и ты не приложишь доказательство.

---

## Проект

Telegram-бот для проверки компаний по ИНН / ОГРН / названию через DaData API.

**Стек:** Python 3.11+, aiogram 3, FastAPI, uvicorn, asyncpg, httpx, cachetools.
**Деплой:** Amvera (webhook-режим). Telegram вызывает `POST /tg/webhook`.

---

## Структура

```
app/
  main.py          # FastAPI app + lifespan (set_webhook, DB pool)
  bot.py           # aiogram Router: хендлеры команд, inline-кнопок, rate_limit
  config.py        # Переменные окружения (Config-класс)
  dadata_client.py # Async httpx-клиент DaData + TTLCache 15 мин
  db.py            # asyncpg pool, init_db, log_request
  formatters.py    # Форматирование ответов для Telegram (Markdown v1)
  rate_limit.py    # Per-user throttle: 1 запрос / 0.5 сек
tests/
  test_dadata_client.py
  test_formatters.py
  test_hardening.py
  test_rate_limit.py
  test_validation.py
```

---

## Настройка и запуск

```bash
# Установить зависимости
pip install -r requirements.txt

# Запустить все тесты (ВСЕГДА делай это перед коммитом)
pytest -q

# Запустить сервер локально
uvicorn app.main:app --host 0.0.0.0 --port 3000
```

Переменные окружения для локального запуска:

| Переменная          | Обязательна | Описание |
|---------------------|-------------|----------|
| `TELEGRAM_BOT_TOKEN`| ✅           | Токен бота от @BotFather |
| `DADATA_API_KEY`    | ✅           | API-ключ DaData |
| `WEBHOOK_URL`       | ✅           | Базовый URL сервиса (без `/tg/webhook`) |
| `POSTGRES_HOST`     | ❌           | Включает логирование запросов в PostgreSQL |
| `POSTGRES_PORT`     | ❌           | Порт PostgreSQL (по умолчанию `5432`) |
| `POSTGRES_DB`       | ❌           | Имя базы данных |
| `POSTGRES_USER`     | ❌           | Пользователь PostgreSQL |
| `POSTGRES_PASSWORD` | ❌           | Пароль PostgreSQL |

---

## Архитектурные правила

### 1. Только Webhook-режим
Бот работает исключительно через webhook. Polling не используется. Не добавляй `executor.start_polling()` и аналоги.

### 2. Markdown v1 (не MarkdownV2)
Все сообщения отправляются с `parse_mode="Markdown"`. Специальные символы для экранирования: `` _ * ` [ ``. Функция `_md()` в `formatters.py` экранирует именно их. Не переключай на MarkdownV2 без полного обновления `_md()` и всех форматтеров.

### 3. Callback data ≤ 64 байт
Telegram ограничивает поле `callback_data` до 64 байт. Ключ контекста — ИНН (10–12 цифр) или ОГРН (13–15 цифр). Текущий формат `"action:1234567890"` укладывается в лимит. Не расширяй структуру callback_data без проверки длины.

### 4. Кэш партий (`bot.py`)
`_context_cache` — `TTLCache(maxsize=1000, ttl=600)` из `cachetools`. Хранит `suggestion`-объект DaData целиком. Ключ: `"party:{inn_or_ogrn}"`. По истечении TTL кнопки показывают «Кэш истёк» — это штатное поведение.

### 5. Кэш DaData (`dadata_client.py`)
`_cache` — `TTLCache(maxsize=512, ttl=900)`. Ключ строится из URL и отсортированных параметров запроса. Кэш не персистентен; при перезапуске обнуляется.

### 6. Rate limit
`check_rate_limit(user_id)` — async-функция с глобальным `asyncio.Lock`. Пропускает не более 1 запроса в 0,5 сек на пользователя. Не заменяй на синхронный вариант.

### 7. DaData: двойной вызов
`find_party_universal()` всегда делает два запроса: сначала `suggest/party` (для поиска по названию), затем `findById/party` (для получения полных данных по ИНН из первого результата). Не упрощай до одного запроса.

### 8. Форматирование дат
`_format_date(val)` в `formatters.py` принимает Unix timestamp в миллисекундах (целое число) — именно в таком виде DaData возвращает `registration_date`. Не убирай преобразование.

### 9. PostgreSQL — опциональна
Логирование в БД включается только если заданы все четыре `POSTGRES_*` переменные. Бот работает без PostgreSQL. Ошибки записи в БД логируются как WARNING, но не прерывают обработку.

---

## Конвенции кода

- **Все I/O — async/await.** Синхронных блокирующих вызовов в хендлерах нет.
- **`from __future__ import annotations`** — в каждом файле.
- **Типизация.** Аннотации на всех публичных функциях. Тип импортируется из `typing` или встроенный (Python 3.10+).
- **Логирование.** `logger = logging.getLogger(__name__)` в каждом модуле. `logger.exception()` для неожиданных ошибок, `logger.warning()` для ожидаемых деградаций.
- **Нет print().** Только `logging`.
- **Хендлеры в `bot.py`.** Бизнес-логика выноси в отдельные модули; хендлеры остаются тонкими.
- **Форматтеры в `formatters.py`.** Каждая функция принимает `suggestion: dict[str, Any]` (объект из DaData) и возвращает `str`.

---

## Тесты

Тесты покрывают:
- Валидацию ИНН/ОГРН (`test_validation.py`)
- Форматтеры (`test_formatters.py`)
- DaData-клиент с моками httpx (`test_dadata_client.py`)
- Rate limit (`test_rate_limit.py`)
- Безопасность и edge-cases (`test_hardening.py`)

Перед любым коммитом:
```bash
pytest -q
```
Все тесты должны проходить. Если добавляешь новый модуль или функцию — добавь тест.

---

## Чего не делать

- Не добавляй `time.sleep()` или синхронные задержки в async-код.
- Не храни секреты (токены, ключи) в коде или тестах.
- Не переключайся на MarkdownV2 частично — только целиком по всему проекту.
- Не используй `global` переменные кроме `db_pool` в `bot.py` (уже есть `set_db_pool`).
- Не добавляй polling; бот работает только через webhook.
- Не трогай `AGENTS.md` без явного указания.
