# Ревизия багов — Jordan Agent

Полная ревизия кодовой базы. Дата: 2026-04-14.

---

## Критические (CRASH)

### B01. `embeddings._unpack_floats` — crash на повреждённом blob

**Файл:** `library/_core/kb/embeddings.py:54–55`
**Категория:** CRASH (`struct.error`)

`_unpack_floats(blob, dim)` вызывает `struct.unpack(f'{dim}f', blob)` без проверки `len(blob) == 4 * dim`. Любая порча БД, ручная смена `dimensions` или несовместимый старый blob вызывает `struct.error` в цикле `hybrid_search`.

**Воспроизведение:** В `chunk_embeddings` записать blob длины ≠ `4 * dimensions`, вызвать `hybrid_search()`.

**Статус:** ИСПРАВЛЕНО

---

### B02. `retrieve.load_arbitration_rules` — `"routes": null` → TypeError

**Файл:** `library/_core/runtime/retrieve.py:260–268`
**Категория:** CRASH (`TypeError: NoneType is not iterable`)

При `{"routes": null}` в JSON, `data.get('routes', [])` возвращает `None` (ключ есть, значение null). В кэш попадает `None`, далее `for route in load_arbitration_rules()` → TypeError.

**Воспроизведение:** Файл `SOURCE_ARBITRATION` с `"routes": null`, вызвать `infer_preferred_sources()`.

**Статус:** ИСПРАВЛЕНО

---

### B03. `state._top_name` — не-dict в continuity → AttributeError

**Файл:** `library/_core/session/state.py:37–44`
**Категория:** CRASH (`AttributeError`)

`_top_name` вызывает `x.get(...)` без проверки типа. Если в `open_loops`/`recurring_themes`/`user_patterns` окажется строка или число (битый JSON), будет `AttributeError`.

**Воспроизведение:** `continuity.json` с `"open_loops": ["plain string"]`, вызвать `build_user_profile()`.

**Статус:** ИСПРАВЛЕНО

---

### B04. `retrieval_validator.validate_chunks` — не-dict chunk → crash

**Файл:** `library/_core/runtime/retrieval_validator.py:120–131`
**Категория:** CRASH (`AttributeError`)

Для каждого элемента вызывается `chunk.get(...)`. Если в список попадёт не-словарь — `AttributeError`.

**Воспроизведение:** `validate_chunks("q", [None])`.

**Статус:** ИСПРАВЛЕНО

---

### B05. `build.build` — нет проверки элемента манифеста

**Файл:** `library/_core/kb/build.py:283–289`
**Категория:** CRASH (`KeyError` / `TypeError`)

Для записи без `text_path`/`source_pdf` или если элемент не словарь — прямой доступ `doc['text_path']` падает.

**Воспроизведение:** `"documents": [{}]` в `manifest.json`.

**Статус:** ИСПРАВЛЕНО

---

### B06. `load_quotes` — FK violation на невалидном chunk_id

**Файл:** `library/_core/kb/quotes.py:206–220`
**Категория:** CRASH (`sqlite3.IntegrityError`)

Валидация проверяет наличие ключей, но не значений. При `PRAGMA foreign_keys = ON` невалидный `chunk_id` ломает всю транзакцию.

**Воспроизведение:** В `manual_quotes.json` несуществующий `chunk_id`, вызвать `load_quotes()`.

**Статус:** ИСПРАВЛЕНО

---

## Неверные данные (WRONG_DATA)

### B07. `fts_query` — фоллбэк `'meaning'` при пустых токенах

**Файл:** `library/utils.py:164–165, 181`
**Категория:** WRONG_DATA

При отсутствии слов длиной ≥3 возвращается `'meaning'` — фиксированный запрос, не связанный с вводом пользователя. Гибридный поиск получает нерелевантные результаты.

**Воспроизведение:** `fts_query("я он она")`.

**Статус:** ИСПРАВЛЕНО

---

### B08. `llm_prompt.build_prompt` — `None` тема/принцип/паттерн в промпте

**Файл:** `library/_core/runtime/llm_prompt.py:79–87, 111–113`
**Категория:** WRONG_DATA

Если `raw_selection['selected_theme']` == `None`, `.get('selected_theme', {})` вернёт `None` (ключ есть). Далее `isinstance(None, dict)` — false, и в промпт уходит строка `"Тема: None"`.

**Воспроизведение:** Вопрос без KB-совпадений → пустой `select_frame` → `build_prompt()`.

**Статус:** ИСПРАВЛЕНО

---

### B09. `progress.estimate` — ложный `'moving'` для нового вопроса

**Файл:** `library/_core/session/progress.py:52–54, 61–63`
**Категория:** WRONG_DATA

При вопросе без совпадений с `topic_keywords` и `repeat_count == 0`: `resolved_count = len(all_resolved[-3:])`, что может быть ≥1 → состояние `'moving'`, хотя прогресса по текущему вопросу нет.

**Воспроизведение:** Новый вопрос без тематических ключевых слов при наличии любых resolved_loops.

**Статус:** ИСПРАВЛЕНО

---

### B10. `quotes.normalize_quotes` — дедупликация по первым 160 символам

**Файл:** `library/_core/kb/quotes.py:159–161`
**Категория:** WRONG_DATA / SILENT_LOSS

Две разные цитаты с одинаковым префиксом в 160 символов: вторая тихо отбрасывается.

**Воспроизведение:** Два кандидата с идентичными первыми 160 символами, но разным хвостом.

**Статус:** ИСПРАВЛЕНО

---

## Тихая потеря данных (SILENT_LOSS)

### B11. `fs_store.put_json` — запись не атомарная

**Файл:** `library/_adapters/fs_store.py:56–62`
**Категория:** SILENT_LOSS

Прямой `write_text` перезаписывает файл. При обрыве процесса — обрезанный JSON → следующее `get_json` → `JSONDecodeError` → fallback на default (потеря состояния).

**Воспроизведение:** Kill процесса во время `put_json`.

**Статус:** ИСПРАВЛЕНО

---

## Итого

| # | Категория | Файл | Описание | Статус |
|---|-----------|------|----------|--------|
| B01 | CRASH | embeddings.py | struct.unpack на неверном blob | ИСПРАВЛЕНО |
| B02 | CRASH | retrieve.py | routes: null → TypeError | ИСПРАВЛЕНО |
| B03 | CRASH | state.py | не-dict в continuity | ИСПРАВЛЕНО |
| B04 | CRASH | retrieval_validator.py | не-dict chunk | ИСПРАВЛЕНО |
| B05 | CRASH | build.py | невалидный элемент манифеста | ИСПРАВЛЕНО |
| B06 | CRASH | quotes.py | FK violation на chunk_id | ИСПРАВЛЕНО |
| B07 | WRONG_DATA | utils.py | fts_query → 'meaning' | ИСПРАВЛЕНО |
| B08 | WRONG_DATA | llm_prompt.py | None в промпте | ИСПРАВЛЕНО |
| B09 | WRONG_DATA | progress.py | ложный 'moving' | ИСПРАВЛЕНО |
| B10 | WRONG_DATA | quotes.py | дедупликация по 160 символам | ИСПРАВЛЕНО |
| B11 | SILENT_LOSS | fs_store.py | неатомарный put_json | ИСПРАВЛЕНО |
