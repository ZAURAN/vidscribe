# 01 — Общее ядро: пакет vidscribe и движок MLX

**Требования:** R01, R03, R05, R09i, R10i, R13i, A02
**Зависит от:** —
**Зона:** `vidscribe/` (кроме `vidscribe/engines/scribe.py` и `vidscribe/engines/whisper.py`) · `pyproject.toml` · `bin/vidscribe` · `tests/` (кроме `tests/test_scribe.py` и `tests/test_whisper.py`)
**Волна:** 1
**Ревью:** да — фундамент
**Модель:** сильная

## Что должно заработать

Bash-скрипт `bin/vidscribe` становится Python-пакетом `vidscribe`, который ведёт себя как оригинал на любой ОС: скачивание по ссылке, проверка дорожек, пустой транскрипт у видео без звука, srt+txt для видео, перенос скачанного видео, предупреждение «ends early», очистка через 3 дня, печать путей. Движок MLX из оригинала перенесён без изменений поведения. Движки scribe и whisper в этом таске — только места в выборе движка: `select` и `get` знают их имена, а сами модули пишет таск 02. Пока модулей нет, выбор их не предлагает (`available()` недоступно → движок считается неустановленным).

## Из брифа, дословно

> «адаптируй тогда все что нужно и сделай с этого правильный скилл чтобы эта система работала как на маках так и на винде»
> «А мы можем всю его систему адаптировать под виндовс ещё?»

## Разделы спецификации

Истории 1–12, 26, 27; Решения по реализации — пакет, yt-dlp, ffmpeg, выбор движка, патч MLX, тесты. Границы — `interfaces.md` (cli, media, subs, engines/__init__, mlx). Поведение оригинала — `notes.md` и `git show 0eb1386:bin/vidscribe`.

## Критерии приёмки

- [ ] `pyproject.toml` описывает пакет `vidscribe` с точкой входа `vidscribe = vidscribe.cli:main`, зависимостью `yt-dlp` и extras `local`/`cuda` из `interfaces.md`; `uv tool install --force --python 3.12 .` ставит рабочую команду `vidscribe` (проверить `vidscribe -h`, затем `uv tool uninstall vidscribe`)
- [ ] `vidscribe/engines/mlx_patch.py` совпадает байт в байт с телом heredoc между `<<'PY'` и `PY` в оригинальном скрипте (тест сверяет с `git show 0eb1386:bin/vidscribe`, если git и коммит доступны, иначе с записанным sha256)
- [ ] `mlx.command(...)` строит ту же команду, что оригинал: `--model --audio --output-path --format --max-tokens (8192+32*dur) --max-parallel-segments (32 при ≥16 GiB, иначе 8)` и `--language`/`--context` только когда заданы (тест)
- [ ] `engines.select`: явный `-e` или `VIDSCRIBE_ENGINE` побеждает; на macOS arm64 с `mlx_audio.stt.generate` → mlx; иначе ключ `ELEVENLABS_API_KEY` → scribe; иначе установленный faster-whisper → whisper; иначе выход 1 с подсказкой под ОС (тест с подменой платформы, PATH и окружения; значение ключа не попадает в вывод)
- [ ] Видео без звука → пустые txt и srt, `video: <абсолютный путь>` для абсолютного и относительного входа; с `-a` → `vidscribe: no audio track to transcribe` и код 1 (порт `tests/silent-video.sh` в Python; sh-файл удалён)
- [ ] Видео со звуком через подставной движок → srt и txt рядом, txt в stdout, `engine: …` и `transcript: …` в stderr; srt, чья последняя реплика кончается на 30+ с раньше конца, даёт `WARNING: last cue … transcript ends early` (тест)
- [ ] Путь с кириллицей и пробелом (`тест видео/клип.mp4`) работает, кириллический текст транскрипта выводится в UTF-8 без ошибок кодировки (тест)
- [ ] `-v`, `--at`, `--scan` печатают сообщение «was removed» оригинала и код 1; несуществующий файл → `no such file: …`; без ffmpeg на PATH → ошибка с командой установки для текущей ОС (тест)
- [ ] `prune` удаляет из `ROOT/{transcripts,videos,frames}` только записи старше 3 дней; `ROOT` = `/tmp/vidscribe` на POSIX и `%TEMP%\vidscribe` на Windows (тест)
- [ ] `bin/vidscribe` — короткий shim, запускающий пакет из checkout; `python -m unittest discover -s tests -v` проходит на этом ПК
