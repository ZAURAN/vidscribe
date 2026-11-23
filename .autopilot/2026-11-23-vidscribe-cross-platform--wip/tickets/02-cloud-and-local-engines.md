# 02 — Движки Scribe и локальный Whisper

**Требования:** R02, R06, R08i, A01, A03
**Зависит от:** 01
**Зона:** `vidscribe/engines/scribe.py` · `vidscribe/engines/whisper.py` · `tests/test_scribe.py` · `tests/test_whisper.py`
**Волна:** 2
**Ревью:** да — секреты
**Модель:** сильная

## Что должно заработать

`vidscribe -e scribe <видео>` отправляет звук в ElevenLabs Scribe и пишет текст с пометками говорящих и звуков. `vidscribe -e whisper <видео>` распознаёт речь локально через faster-whisper на видеокарте NVIDIA этого ПК (RTX 4070), а без CUDA — на процессоре. На Windows с ключом по умолчанию работает Scribe, без ключа — Whisper, если он установлен.

## Из брифа, дословно

> «а если Scribe использовать?»
> «давай его поставим»
> «так и на винде»

## Разделы спецификации

Истории 13–20; Решения по реализации — Scribe, whisper, Python 3.12. Границы — `interfaces.md` (engines/scribe, engines/whisper, контракт `transcribe`). Справка по API: https://elevenlabs.io/docs/api-reference/speech-to-text/convert.md — поля `model_id`, `file`, `language_code`, `diarize`, `tag_audio_events`, `timestamps_granularity`, `num_speakers`, `keyterms` (повторяемое поле); ответ: `language_code`, `words[]` с `text`, `start`, `end`, `type` (`word`/`spacing`/`audio_event`), `speaker_id`.

## Критерии приёмки

- [ ] Scribe: запрос — multipart с `model_id` (по умолчанию `scribe_v3`, `-m` меняет), `diarize=true`, `tag_audio_events=true`, `timestamps_granularity=word`, `language_code` из `-l`, `num_speakers` из `-n`, каждый термин из `-c "A, B"` — отдельным полем `keyterms`; звук — mono mp3 64 кбит/с; заголовок `xi-api-key` (тест с подменой `urlopen`, без сети)
- [ ] Scribe: слова собираются в реплики по правилам спецификации (смена говорящего, пауза >1 с, конец предложения, >7 с), `[speaker_N]` — только когда говорящих больше одного, звуки как `(laughter)`; srt, vtt и txt пишутся через `subs`; `-f json` — сырой ответ (тест)
- [ ] Scribe: без ключа → понятная ошибка: где взять ключ (elevenlabs.io) и как задать его самому на текущей ОС (`setx` на Windows, `export` в `~/.zshrc` на Mac); HTTP-ошибка → `ElevenLabs API error <код>: <сообщение>`, сетевая → `cannot reach ElevenLabs: …`, код 1, без повторов; значение ключа не появляется ни в stdout, ни в stderr, ни в файлах (тест)
- [ ] Перед отправкой в stderr есть строка `engine: scribe (audio is uploaded to ElevenLabs)` — согласовать с тем, как `cli` из таска 01 печатает `engine:` (правка `cli.py` ради одной этой строки допустима)
- [ ] Whisper: `available()` истинно, только если импортируется faster_whisper; модель по умолчанию `large-v3-turbo`, `-m` меняет; `-l` → язык, `-c` → `hotwords`; `vad_filter=True`; сегменты → `subs` в нужном формате, `-f json` — сегменты с языком (тест с подставной моделью)
- [ ] Whisper: на Windows перед импортом добавляются папки DLL из `site-packages/nvidia/*/bin`; CUDA float16, при ошибке — CPU int8 и `warning: CUDA unavailable (...), using CPU` (тест с подменой)
- [ ] Whisper на настоящем ПК: `uv tool install --force --python 3.12 ".[local,cuda]"`, затем `vidscribe -e whisper` на коротком ролике с английской речью (`https://www.youtube.com/watch?v=jNQXAC9IVRw`) — текст осмысленный, в stderr видно, CUDA или CPU; вывод приложить к отчёту; после проверки оставить установленным
- [ ] Scribe на настоящем API: только если `ELEVENLABS_API_KEY` уже задан в окружении — прогнать тот же ролик с `-e scribe -a`; если не задан — написать в отчёте «не проверено, нет ключа»; значение ключа не выводить
