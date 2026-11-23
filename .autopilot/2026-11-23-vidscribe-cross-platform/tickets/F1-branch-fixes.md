# F1 — Правки по общему ревью

**Требования:** R10i, R06, R02, A01
**Зависит от:** —
**Зона:** `vidscribe/cli.py` · `vidscribe/engines/whisper.py` · `vidscribe/engines/scribe.py` · `tests/test_cli.py` · `tests/test_whisper.py` · `tests/test_scribe.py`
**Волна:** 3
**Ревью:** да — ремонт ветки
**Модель:** сильная

## Что должно заработать

Предупреждение «transcript ends early» срабатывает и для видео по ссылке. Опечатка в имени файла, локальный движок без установки, обрыв ответа Scribe и сбой CUDA во время распознавания дают понятное сообщение или переход на процессор, а не трейсбек.

## Из брифа, дословно

> «А мы можем всю его систему адаптировать под виндовс ещё?»
> «давай его поставим»

## Разделы спецификации

Истории 5, 8, 15, 19, 20.

## Критерии приёмки

- [ ] FIX NOW · vidscribe/cli.py:107+112 — для скачанного видео длительность для проверки «ends early» берётся до переноса файла (или по новому пути); тест в test_cli с подменённым `media.download`, возвращающим файл внутри tmp, получает `WARNING: last cue … transcript ends early` и проверяет перенос в `ROOT/videos` и строку `video:` с новым путём
- [ ] vidscribe/cli.py:69 — для локального пути `no such file: …` проверяется до `engines.select` (тест: нет движка и нет файла → `no such file`)
- [ ] vidscribe/engines/whisper.py:172/193 — `-e whisper` без faster-whisper печатает `vidscribe: …` с подсказкой про установку (`install.ps1 -Local` на Windows, `uv tool install --force --python 3.12 "<repo>[local]"` в общем случае) и код 1, без трейсбека (тест)
- [ ] vidscribe/engines/whisper.py:173-196 — ошибка CUDA при распознавании (не только при создании модели) ведёт к `warning: CUDA unavailable (...), using CPU` и повтору на CPU int8 (тест с подменой)
- [ ] vidscribe/engines/scribe.py:90-91 — обрыв ответа (`http.client.IncompleteRead`/любой `http.client.HTTPException`) → `cannot reach ElevenLabs: …`, ответ 200 не в JSON → `ElevenLabs API error 200: invalid response`, код 1, без трейсбека и без ключа (тест)
