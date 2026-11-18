# БАЗОВАЯ ТОЧКА ТРЕНАЖЁРА (ЭТАП 1 ПЛАНА)

Дата: 18 ноября 2026 года. Состояние зафиксировано перед началом
изменений по плану `docs/PLAN-TRENAZHER-K71.md`.

## Диск и библиотека

- `~/.besm6/2348`, md5 `ed59f2c9c0c8a8e4625da31e356b3abf`.
- Зона `2700(8)` — 6 зон, 25 входов:
  `GLDIAL`, `PROGRAM`, `GLANG`, `GLVOD`, `GLSC`, `GLBUR`, `GLSEED`,
  `GLSOST`, `GLT`, `GLSET`, `JUDG`, `DISPL`, `FRAME`, `TURB`, `SBRND`,
  `SBATM`, `PRVIN`, `PROGC`, `GLAUTO`, `MOTOR`, `PROIZV`, `INITD`,
  `KUTMER`, `*APGAIN*`, `*TTXDAT*`.

## Контрольные точки

1. **Исторические сценарии:** `python3 TOOLS/calib/scenarios.py verify`
   — `OK=10, отклонений=0`.
2. **Вызов диалога:** `GLCALL-2700.B6` под pty — `PASRED: 11/11`,
   `WHAT отвечено: 0` (подавление `L0` + `PASTEL[3]:=[48]`),
   `OCENKA= 4`, `КОНЕЦ ЗАДАЧИ`, код выхода 0.

## Правило регрессии

После каждого этапа плана должны выполняться обе контрольные точки.
Изменение md5 диска допустимо только при пересборке PERSO через
`TOOLS/install-2348.sh`; каталог зоны 2700 при этом должен сохранить
все 25 входов.

## Воспроизведение

```bash
cd ~/Yandex.Disk/re-glissade
md5sum ~/.besm6/2348
python3 TOOLS/calib/scenarios.py verify
python3 TOOLS/run_gldial_pty.py <каталог>/GLCALL-2700.B6 240
```
