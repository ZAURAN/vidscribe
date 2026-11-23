# 03 — Установщики, скилл и документация для обеих ОС

**Требования:** R04, R07i, R11i, R12i, R14i
**Зависит от:** 01
**Зона:** `install.sh` · `install.ps1` · `skill/` · `README.md` · `docs/usage.md` · `docs/decisions/0010-cross-platform-engines.md` · `docs/decisions/README.md` · `AGENTS.md` (только таблица «Команды» между маркерами)
**Волна:** 2
**Ревью:** нет
**Модель:** обычная

## Что должно заработать

На Windows `install.ps1` одной командой ставит всё нужное: ffmpeg и uv (если их нет), программу `vidscribe` на PATH и скилл в `~/.claude/skills/vidscribe`. На Mac `install.sh` делает то же, что раньше, плюс ставит пакет и скилл. Один SKILL.md верен на обеих ОС. README и usage рассказывают про обе ОС и три движка, ADR-0010 объясняет, почему появилось облако.

## Из брифа, дословно

> «сделай с этого правильный скилл чтобы эта система работала как на маках так и на винде»
> «А мы можем всю его систему адаптировать под виндовс ещё?»

## Разделы спецификации

Истории 17, 19, 21–25; все Решения по реализации; Вне рамок. Границы — `interfaces.md` («Install and skill»), флаги — раздел `cli`. Исходные тексты — текущие `README.md`, `docs/usage.md`, `skill/SKILL.md`, `install.sh`.

## Критерии приёмки

- [ ] `install.ps1` (Windows PowerShell 5.1 и 7): ставит ffmpeg (`winget install Gyan.FFmpeg`) и uv (`winget install astral-sh.uv`), только если их нет; `uv tool install --force --python 3.12 <repo>` (с ключом `-Local` — `<repo>[local,cuda]`); `uv tool update-shell` или подсказка про PATH; копирует `skill/` в `~/.claude/skills/vidscribe`, сначала очистив эту папку; печатает, как задать `ELEVENLABS_API_KEY` самому, и никогда не спрашивает ключ
- [ ] `install.ps1 -Local` запущен на этом ПК дважды подряд без ошибок; после него `vidscribe -h` работает, а в `~/.claude/skills/vidscribe` лежат только файлы из `skill/` (старого `vidscribe.py` там нет)
- [ ] `install.sh` (macOS arm64): прежние шаги brew и mlx-audio, затем `uv tool install --force --python 3.12 <repo>` и копирование скилла; старая ссылка `~/.local/bin/vidscribe` на bash-скрипт убирается, чтобы не заслонять команду uv; синтаксис проверен `bash -n`
- [ ] `skill/SKILL.md`: одна команда `vidscribe` для обеих ОС, пути — только «напечатанный путь», три движка и выбор через `-e`, правило «перед закрытыми видео спроси пользователя, если движок scribe», предупреждения (`no audio track`, `transcript ends early`, `transcript cut off`, повтор одного слова, CUDA→CPU), пометки `[speaker_N]` и `(laughter)`; frontmatter `name`/`description` валиден; про ключ — «пользователь задаёт сам, никогда не проси его в чате»
- [ ] `README.md` и `docs/usage.md`: установка на Mac и Windows, таблица движков (где работает, когда по умолчанию, платно ли, уходит ли звук с устройства), все флаги включая `-e` и `-n`, переменные `ELEVENLABS_API_KEY`, `VIDSCRIBE_ENGINE`, `VIDSCRIBE_MODEL`, `VIDSCRIBE_OUTDIR`, папки результатов на каждой ОС, удаление; честно сказано, что цифры бенчмарка измерены на MLX
- [ ] `docs/decisions/0010-cross-platform-engines.md` в формате остальных ADR (Status, Date 2026-11-23, Context, Decision, Alternatives considered, Consequences) и строка в таблице `docs/decisions/README.md`; ADR-0001 не переписан
- [ ] Таблица «Команды» в `AGENTS.md` между маркерами заполнена: установка (Mac, Windows), запуск из checkout, проверка
