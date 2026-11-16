# Командний рядок `sipl`

Після `pip install -e .` доступна команда `sipl`. Ті самі команди працюють через `python -m sipl`.

```
sipl parse FILE [--json]
sipl check FILE [--json]
sipl run   FILE [ЗМІННА=ЧИСЛО ...] [--max-iterations N] [--json]
sipl trace FILE [ЗМІННА=ЧИСЛО ...] [--max-iterations N] [--json]
sipl tree    FILE [--format text|dot|svg] [-o ФАЙЛ] [--json]
sipl compare FILE [-o ФАЙЛ] [--json]
```

| Команда | Що робить |
|---|---|
| `parse` | розбирає програму й показує AST |
| `check` | лише перевіряє синтаксис |
| `run` | виконує програму й показує кінцевий стан |
| `trace` | виконує програму й показує всі події виконання |
| `tree` | будує дерево синтаксичного виводу (parse tree), див. [visualization.md](visualization.md) |
| `compare` | HTML-сторінка: parse tree і AST поряд, див. [visualization.md](visualization.md) |

* `ЗМІННА=ЧИСЛО` задає початковий стан, наприклад `X=2 Y=10` або `x=-4`.
* `--max-iterations N` встановлює ліміт ітерацій циклів (типово 100000); `0` вимикає ліміт.
* `--format` (лише `tree`) — `text` (типово), `dot` (Graphviz) або `svg` (готова картинка).
* `-o ФАЙЛ` (`tree`, `compare`) записує результат у файл в UTF-8 замість stdout.
* `--json` виводить результат на stdout у форматі JSON (див. нижче); для `tree` він має пріоритет над `--format`.

## Приклади

```
> sipl run examples/power.sipl X=2 Y=10
X = 2
Y = 0
R = 1024

> sipl parse examples/gcd.sipl
Program [1:1]
  While [2:3]
    Not [2:9]
      Compare op='=' [2:12]
...

> sipl trace examples/power.sipl X=3 Y=1
[2:3]    BeforeStatement statement='Assign'
[2:3]    VariableChanged name='R' old=None new=1
...
         Finished state={'X': 3, 'Y': 0, 'R': 3}
```

`[рядок:колонка]` — місце оператора чи вузла у файлі.

## Коди завершення

| Код | Значення |
|---|---|
| 0 | успіх |
| 1 | синтаксична помилка в програмі |
| 2 | помилка використання: немає файлу, неправильний `ЗМІННА=ЧИСЛО`, невідома команда чи опція |
| 3 | помилка виконання: невизначена змінна, ділення на нуль, перевищено ліміт ітерацій |

У текстовому режимі результат друкується в stdout, а помилка — в stderr: `Помилка: Рядок 1, колонка 12: змінна 'y' не визначена`.

## JSON-формат

Кожна команда з `--json` друкує один JSON-об'єкт:

```json
{
  "ok": true,
  "command": "run",
  "state": {"X": 2, "Y": 0, "R": 1024}
}
```

| Поле | Коли є | Значення |
|---|---|---|
| `ok` | завжди | `true`, якщо код завершення 0 |
| `command` | завжди | `"parse"`, `"check"`, `"run"`, `"trace"`, `"tree"` або `"compare"` |
| `ast` | `parse`, якщо немає помилки | AST (формат нижче) |
| `state` | `run`, якщо немає помилки | кінцевий стан `{"змінна": число}` |
| `events` | `trace`, якщо синтаксис коректний | список подій; якщо виконання впало, він закінчується подією `Failed` |
| `tree` | `tree`, `compare`, якщо немає помилки | дерево виводу (формат у [visualization.md](visualization.md)) |
| `ast_tree`, `comparison` | `compare`, якщо немає помилки | AST для малювання і статистика порівняння |
| `error` | якщо `ok` = `false` | `{"kind", "message", "line", "column"}` |

`error.kind` має одне зі значень `"syntax"` (код 1), `"usage"` (код 2) або `"runtime"` (код 3).
Поля `line` і `column` дорівнюють `null`, якщо позиція невідома (наприклад, для `usage`).

Помилки самих аргументів командного рядка (невідома команда, пропущений файл) обробляє `argparse`. Він друкує текстове повідомлення в stderr навіть із `--json` і завершується з кодом 2.

### Вузол AST

```json
{"type": "Assign", "span": {"line": 2, "column": 3, "end_line": 2, "end_column": 9},
 "name": "R", "expr": {"type": "Num", "span": {...}, "value": 1}}
```

`type` — ім'я класу з `sipl/ast.py`, далі йдуть `span` і поля цього класу. Дочірні вузли записуються такими самими об'єктами, а `Seq.statements` — списком.

### Подія trace

```json
{"event": "VariableChanged", "name": "R", "old": null, "new": 1, "span": {...}}
```

`event` — ім'я класу з `sipl/interpreter/events.py`, далі йдуть поля цієї події (таблиця подій є в README).
