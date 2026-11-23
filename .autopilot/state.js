window.STATE =
{
  "version": 2,
  "slug": "vidscribe-cross-platform",
  "dir": "2026-11-23-vidscribe-cross-platform--wip",
  "title": "vidscribe для Mac и Windows",
  "mode": "full",
  "depth": "deep",
  "tier": "T2",
  "briefFile": "2026-11-23-brief.md",
  "memoryFile": "AGENTS.md",
  "memoryOwner": "autopilot",
  "skillDir": "C:/Users/ganba/.claude/skills/autopilot",
  "baseCommit": null,
  "startedAt": "2026-11-23T15:40:35+02:00",
  "updatedAt": "2026-11-23T15:48:13+02:00",
  "finishedAt": null,
  "stages": [
    {
      "id": "preflight",
      "status": "done",
      "startedAt": "2026-11-23T15:40:35+02:00",
      "finishedAt": "2026-11-23T15:40:59+02:00"
    },
    {
      "id": "manifest",
      "status": "done",
      "startedAt": "2026-11-23T15:40:59+02:00",
      "finishedAt": "2026-11-23T15:41:51+02:00"
    },
    {
      "id": "briefing",
      "status": "skipped",
      "startedAt": "2026-11-23T15:41:51+02:00",
      "finishedAt": "2026-11-23T15:42:26+02:00",
      "note": "полный автомат — самобрифинг"
    },
    {
      "id": "spec",
      "status": "done",
      "startedAt": "2026-11-23T15:42:28+02:00",
      "finishedAt": "2026-11-23T15:48:03+02:00"
    },
    {
      "id": "plan",
      "status": "active",
      "startedAt": "2026-11-23T15:48:03+02:00"
    },
    {
      "id": "build",
      "status": "pending"
    },
    {
      "id": "review",
      "status": "pending"
    },
    {
      "id": "final",
      "status": "pending"
    }
  ],
  "requirements": {
    "total": 14,
    "done": 0,
    "inTicket": 14,
    "inSpec": 0,
    "placeholder": 0,
    "deferred": 0,
    "dropped": 0
  },
  "tickets": [
    {
      "id": "01",
      "title": "Общее ядро: пакет vidscribe и движок MLX",
      "requirements": [
        "R01",
        "R03",
        "R05",
        "R09i",
        "R10i",
        "R13i",
        "A02"
      ],
      "blockedBy": [],
      "wave": 1,
      "zone": [
        "vidscribe/",
        "vidscribe/engines/scribe.py",
        "vidscribe/engines/whisper.py",
        "pyproject.toml",
        "bin/vidscribe",
        "tests/",
        "tests/test_scribe.py",
        "tests/test_whisper.py"
      ],
      "review": "да — фундамент",
      "model": "сильная",
      "status": "pending",
      "retries": 0,
      "repairs": 0
    },
    {
      "id": "02",
      "title": "Движки Scribe и локальный Whisper",
      "requirements": [
        "R02",
        "R06",
        "R08i",
        "A01",
        "A03"
      ],
      "blockedBy": [
        "01"
      ],
      "wave": 2,
      "zone": [
        "vidscribe/engines/scribe.py",
        "vidscribe/engines/whisper.py",
        "tests/test_scribe.py",
        "tests/test_whisper.py"
      ],
      "review": "да — секреты",
      "model": "сильная",
      "status": "pending",
      "retries": 0,
      "repairs": 0
    },
    {
      "id": "03",
      "title": "Установщики, скилл и документация для обеих ОС",
      "requirements": [
        "R04",
        "R07i",
        "R11i",
        "R12i",
        "R14i"
      ],
      "blockedBy": [
        "01"
      ],
      "wave": 2,
      "zone": [
        "install.sh",
        "install.ps1",
        "skill/",
        "README.md",
        "docs/usage.md",
        "docs/decisions/0010-cross-platform-engines.md",
        "docs/decisions/README.md",
        "AGENTS.md"
      ],
      "review": "нет",
      "model": "обычная",
      "status": "pending",
      "retries": 0,
      "repairs": 0
    }
  ],
  "tests": null,
  "debt": {
    "placeholders": [],
    "assumptions": [
      "Scribe по умолчанию на Windows при заданном ключе, иначе локальный Whisper",
      "На Mac по умолчанию остаётся MLX, Scribe по флагу -e scribe",
      "Добавлен локальный движок faster-whisper для Windows (A01)",
      "Установка на Windows — install.ps1 через winget и uv tool"
    ],
    "emptyEnv": []
  },
  "additions": [],
  "coverage": {
    "found": 2,
    "fixed": 0,
    "deferred": 2,
    "items": [
      "R02 — Scribe на настоящем API не проверить без ключа пользователя",
      "R05 — MLX на настоящем Mac не проверить на этом ПК"
    ]
  },
  "concerns": [],
  "blind": null,
  "beats": [
    "2026-11-23T15:40:35+02:00",
    "2026-11-23T15:40:59+02:00",
    "2026-11-23T15:41:49+02:00",
    "2026-11-23T15:41:51+02:00",
    "2026-11-23T15:42:20+02:00",
    "2026-11-23T15:42:21+02:00",
    "2026-11-23T15:42:23+02:00",
    "2026-11-23T15:42:24+02:00",
    "2026-11-23T15:42:26+02:00",
    "2026-11-23T15:42:28+02:00",
    "2026-11-23T15:48:03+02:00",
    "2026-11-23T15:48:05+02:00",
    "2026-11-23T15:48:07+02:00",
    "2026-11-23T15:48:10+02:00",
    "2026-11-23T15:48:13+02:00"
  ],
  "rev": 16,
  "waiting": null,
  "waits": [],
  "log": [
    {
      "t": "2026-11-23T15:40:35+02:00",
      "k": "init"
    },
    {
      "t": "2026-11-23T15:40:59+02:00",
      "k": "stage",
      "id": "manifest",
      "act": "start"
    },
    {
      "t": "2026-11-23T15:41:51+02:00",
      "k": "stage",
      "id": "briefing",
      "act": "start"
    },
    {
      "t": "2026-11-23T15:42:20+02:00",
      "k": "add",
      "key": "debt.assumptions",
      "n": 1
    },
    {
      "t": "2026-11-23T15:42:21+02:00",
      "k": "add",
      "key": "debt.assumptions",
      "n": 1
    },
    {
      "t": "2026-11-23T15:42:23+02:00",
      "k": "add",
      "key": "debt.assumptions",
      "n": 1
    },
    {
      "t": "2026-11-23T15:42:24+02:00",
      "k": "add",
      "key": "debt.assumptions",
      "n": 1
    },
    {
      "t": "2026-11-23T15:42:26+02:00",
      "k": "stage",
      "id": "briefing",
      "act": "skip",
      "note": "полный автомат — самобрифинг"
    },
    {
      "t": "2026-11-23T15:42:28+02:00",
      "k": "gate",
      "g": "G1",
      "ok": false,
      "open": 14,
      "total": 14
    },
    {
      "t": "2026-11-23T15:42:28+02:00",
      "k": "stage",
      "id": "spec",
      "act": "start"
    },
    {
      "t": "2026-11-23T15:48:03+02:00",
      "k": "stage",
      "id": "plan",
      "act": "start"
    },
    {
      "t": "2026-11-23T15:48:05+02:00",
      "k": "gate",
      "g": "G2",
      "ok": true,
      "found": 2,
      "fixed": 0,
      "deferred": 2
    },
    {
      "t": "2026-11-23T15:48:07+02:00",
      "k": "tier",
      "v": "T2"
    },
    {
      "t": "2026-11-23T15:48:10+02:00",
      "k": "tickets",
      "n": 3
    },
    {
      "t": "2026-11-23T15:48:13+02:00",
      "k": "gate",
      "g": "G3",
      "ok": true,
      "problems": 0
    }
  ],
  "reqList": [
    {
      "id": "R01",
      "text": "«всю его систему адаптировать под виндовс»",
      "status": "in-ticket"
    },
    {
      "id": "R02",
      "text": "«а если Scribe использовать?» / «давай его поставим»",
      "status": "in-ticket"
    },
    {
      "id": "R03",
      "text": "«адаптируй тогда все что нужно»",
      "status": "in-ticket"
    },
    {
      "id": "R04",
      "text": "«сделай с этого правильный скилл»",
      "status": "in-ticket"
    },
    {
      "id": "R05",
      "text": "«чтобы эта система работала как на маках»",
      "status": "in-ticket"
    },
    {
      "id": "R06",
      "text": "«так и на винде»",
      "status": "in-ticket"
    },
    {
      "id": "R07i",
      "text": "(подразумевается) на Windows ставится одной командой, как install.sh на Mac",
      "status": "in-ticket"
    },
    {
      "id": "R08i",
      "text": "(подразумевается) ключ ElevenLabs не запрашивается в чате и не хранится в репозитории",
      "status": "in-ticket"
    },
    {
      "id": "R09i",
      "text": "(подразумевается) на Mac ничего не ломается: локальный MLX остаётся основным движком, поведение и флаги прежние",
      "status": "in-ticket"
    },
    {
      "id": "R10i",
      "text": "(подразумевается) «вся система» = скачивание по ссылке, расшифровка, srt с таймкодами, сохранённое видео для ffmpeg, предупреждения, очистка через 3 дня — на обеих ОС",
      "status": "in-ticket"
    },
    {
      "id": "R11i",
      "text": "(подразумевается) «правильный скилл» ставится стандартно (npx skills add и копированием в ~/.claude/skills) и одинаково описывает шаги агента на обеих ОС",
      "status": "in-ticket"
    },
    {
      "id": "R12i",
      "text": "(подразумевается) документация (README, usage, решения) говорит правду про обе ОС и про Scribe",
      "status": "in-ticket"
    },
    {
      "id": "R13i",
      "text": "(подразумевается) есть проверки, которые запускаются на обеих ОС",
      "status": "in-ticket"
    },
    {
      "id": "R14i",
      "text": "(подразумевается) временный скилл, поставленный ранее в этом разговоре (~/.claude/skills/vidscribe), заменяется новой версией",
      "status": "in-ticket"
    }
  ],
  "gates": {
    "G1": {
      "ok": false,
      "at": "2026-11-23T15:42:28+02:00",
      "open": 14,
      "total": 14
    },
    "G2": {
      "ok": true,
      "at": "2026-11-23T15:48:05+02:00",
      "found": 2,
      "fixed": 0,
      "deferred": 2
    },
    "G3": {
      "ok": true,
      "at": "2026-11-23T15:48:13+02:00",
      "problems": 0
    }
  },
  "result": null
}
