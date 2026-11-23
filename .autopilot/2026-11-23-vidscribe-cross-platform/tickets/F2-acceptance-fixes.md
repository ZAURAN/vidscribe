# F2 — Правки по слепой приёмке

**Требования:** R04, R07i, R11i, R13i
**Зависит от:** —
**Зона:** `README.md` · `docs/usage.md` · `tests/test_whisper.py`
**Волна:** 4
**Ревью:** нет
**Модель:** обычная

## Что должно заработать

Кто ставит по README, получает эту кроссплатформенную версию, а не оригинал только для Mac. Тесты зелёные и тогда, когда установлен локальный движок с библиотеками CUDA.

## Из брифа, дословно

> «сделай с этого правильный скилл чтобы эта система работала как на маках так и на винде»

## Разделы спецификации

Истории 21, 23–26; «Вне рамок» — публикация форка на GitHub только по просьбе пользователя.

## Критерии приёмки

- [ ] README и docs/usage.md не ведут к оригиналу как к источнику установки: установка описана «из папки этого репозитория» (`cd` в checkout, затем `./install.sh` или `install.ps1`), без `git clone https://github.com/SamuelZ12/vidscribe.git`; ссылка на оригинал остаётся только как «основано на» (upstream, MIT)
- [ ] Строка `npx skills add SamuelZ12/vidscribe` убрана или явно помечена: она ставит исходный скилл только для Mac; для этой версии скилл ставят установщики (копия `skill/` в `~/.claude/skills/vidscribe`)
- [ ] `tests/test_whisper.py::test_windows_adds_nvidia_dll_folders_before_import` не зависит от того, установлены ли настоящие пакеты nvidia: проходит и в чистом Python, и в окружении с `.[local,cuda]` (проверить в обоих — второе: `uv venv --python 3.12 <tmp>/.venv`, `uv pip install --python <tmp>/.venv/Scripts/python.exe ".[local,cuda]"`, затем `<tmp>/.venv/Scripts/python.exe -m unittest discover -s tests`; удалить tmp после)
