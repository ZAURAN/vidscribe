<!-- autopilot:start -->
# vidscribe

Lets AI agents "watch" videos on macOS and Windows: speech becomes a timestamped transcript, the video file is kept so the agent can look at frames with ffmpeg.

## Команды

| Команда | Что делает |
|---------|------------|
| `./install.sh` | Установка на Mac (Apple Silicon): brew, mlx-audio, пакет через uv, скилл |
| `powershell -ExecutionPolicy Bypass -File install.ps1` | Установка на Windows: ffmpeg и uv через winget, пакет через uv, скилл; `-Local` добавляет движок whisper |
| `python -m vidscribe <файл или ссылка>` | Запуск из checkout без установки (в корне репозитория; на Windows `python`, не `python3`) |
| `python -m unittest discover -s tests -v` | Проверка: все тесты; тесты, которым нужен ffmpeg, без него пропускаются |

## Где что

- `vidscribe/cli.py` — разбор аргументов и весь ход запуска; `vidscribe/media.py` — ffmpeg, yt-dlp, папки вывода; `vidscribe/subs.py` — форматы txt/srt/vtt.
- `vidscribe/engines/` — движки `mlx`, `scribe`, `whisper`; выбор в `engines/__init__.py` (`select`).
- `install.sh`, `install.ps1` — установка; `skill/SKILL.md` — скилл, который они копируют в `~/.claude/skills/vidscribe`.
- `bin/vidscribe` — shim для запуска из checkout на Mac/Linux.
- `docs/architecture.md` — поток данных, границы модулей, договорённости.
- `docs/decisions/` — почему так (ADR); `CONTEXT.md` — словарь (движок, cue, piece, kept video).

## Подводные камни

- `core.autocrlf=true` даёт CRLF в рабочей копии; `.gitattributes` держит LF для `bin/vidscribe` и `*.sh`.
- `vidscribe/engines/mlx_patch.py` должен остаться байт в байт с оригиналом (`tests/test_mlx.py` сверяет sha256); mlx на Windows не проверить.
- whisper читает wav через `wave`, не через PyAV: faster-whisper 1.2.1 несовместим с PyAV 19 (`docs/decisions/0013-whisper-reads-wav-directly.md`).
- Scribe не следует переадресациям и не печатает ключ: не заменять `build_opener(_NoRedirect)` на `urlopen` (`docs/decisions/0012-scribe-no-redirects.md`).
- Параллельный `uv tool install` ломает окружение инструмента; ставить по одному.
- Явный `-e` / `VIDSCRIBE_ENGINE` не проверяется на доступность.
- Тексты сообщений (`video:`, `transcript:`, про отсутствие звука) сохранены дословно из оригинала; тесты на них опираются.

## Окружение

- `ELEVENLABS_API_KEY` — ключ движка scribe; его наличие включает scribe в автовыборе.
- `VIDSCRIBE_ENGINE` — движок по умолчанию (`mlx`, `scribe`, `whisper`).
- `VIDSCRIBE_MODEL` — модель для mlx.
- `VIDSCRIBE_OUTDIR` — куда писать транскрипты (по умолчанию `<tmp>/vidscribe/transcripts`).

## Как здесь работает Autopilot

Сборка ведётся навыком `/autopilot`. Требования, спецификация и таски — в `.autopilot/`.
Прогресс — `.autopilot/dashboard.html`. Требование из `manifest.md` может снять
только пользователь. Прерванную сборку продолжает «продолжи автопилот».

### Правка без автопилота

Мелкий баг или доводка после сборки — обычная сессия, без прогона.

Сначала прочитай:
1. `.autopilot/PROGRESS.md` — что не доделано, известные баги, о чём договорились с пользователем.
2. Что правили после последней сборки — первая строка таблицы в «История git».
3. Только если правка их касается: почему сделано так — `docs/decisions/`; что значат слова — `CONTEXT.md`;
   что именно просили — `manifest.md` в папке сборки (указана в начале `PROGRESS.md`).

После правки:
- коммит — по правилам из «История git»;
- строка в «Правки без автопилота» в `PROGRESS.md`: дата — что — почему;
- починенный пункт из «Не доделано» или «Известные баги» — удали;
- договорились с пользователем о том, что следующая сборка не должна пересматривать, —
  строка в «Договорились», его словами.

### История git

Целиком не читай — бери срез под вопрос:

| Вопрос | Команда |
|---|---|
| что правили после последней сборки | `git log --oneline "$(git log -1 --format=%h --grep='^Autopilot: сборка сдана')"..HEAD -- . ':(exclude).autopilot'` |
| всё, что делали ради требования | `git log --oneline --grep="R02"` |
| история файла | `git log --oneline -10 -- <файл>` |
| когда появился или исчез код | `git log --oneline -S "<фрагмент>"` |
| почему строка такая | `git blame -L <с>,<по> <файл>`, затем `git show <sha>` |
| что внутри коммита | `git show --stat <sha>` |

Срез длиннее ~30 коммитов — отдай его субагенту и возьми выжимку в десять строк.

Коммит: заголовок — что (`fix: даты в одном формате`), тело — почему, трейлер
`--trailer "Requirements: R02"`, если правка касается требования из `manifest.md`.
Заголовок `Autopilot: сборка сдана` пишет только автопилот — по нему находят последнюю сборку.
<!-- autopilot:end -->
