# SIPL Language Toolkit

## Обсяг роботи

| Завдання | Що реалізовано | Головний файл | Бали |
|---|---|---|---|
| CORE-01 | граматика за БНФ практикуму та тести на неї | `src/sipl/grammar/sipl.lark` | 0.5 |
| CORE-02 | розбір тексту у власні вузли AST з позиціями | `src/sipl/parser.py`, `src/sipl/ast.py` | 1.5 |
| CORE-03 | виконання програми на стані змінних | `src/sipl/interpreter/__init__.py` | 2.0 |
| CORE-04 | події під час виконання (trace) | `src/sipl/interpreter/events.py` | 1.0 |
| CORE-05 | команда `sipl` з текстовим і JSON-виводом | `src/sipl/cli.py` | 1.0 |
| CORE-06 | набір еталонних тестів для будь-якої реалізації | `conformance/` | 1.0 |
| VIS-01 | дерево синтаксичного виводу | `src/sipl/visualization/__init__.py` | 1.5 |
| VIS-02 | AST поруч із деревом виводу | `src/sipl/visualization/__init__.py` | 1.0 |
| | | **Сума** | **9.5** |

## Як встановити на іншому комп'ютері

Потрібні лише Python 3.10 або новіший і доступ до інтернету (для `pip`). Код правити не треба.

**1. Отримати код.** Через git:
```
git clone https://github.com/andriisushchenko/TP_lab
cd TP_lab
```
або на GitHub натиснути **Code → Download ZIP**, розпакувати архів і відкрити термінал у розпакованій папці.

**2. Створити віртуальне оточення і встановити проєкт** 

Windows (PowerShell):
```
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Linux / macOS:
```
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```
**3. Перевірити, що все працює:**
```
sipl --help
sipl run examples/power.sipl X=2 Y=10
pytest
```
Має з'явитися список команд, потім `R = 1024`, а наприкінці `238 passed`.

## Огляд кожного завдання

У папці `examples/` лежать три програми: `power.sipl` (степінь), `factorial.sipl` (факторіал), `gcd.sipl` (НСД).

**CORE-01 — граматика.** Файл `sipl.lark` записує БНФ із практикуму у вигляді, який розуміє бібліотека Lark. Її перевіряють 14 правильних і 18 неправильних програм із `tests/grammar/`.
```
pytest tests/test_grammar.py --no-cov
```

**CORE-02 — парсер і AST.** Програма перетворюється на дерево з власних класів (`Assign`, `While`, `BinOp` …), у кожного вузла є рядок і колонка. Синтаксична помилка повідомляє, де вона і що там очікувалось.
```
sipl parse examples/power.sipl
sipl check examples/gcd.sipl
```
Для програми `begin x := 1 y := 2 end` (пропущено `;`):
```
Помилка: Рядок 1, колонка 14: неочікуване 'y'; очікувалось: '*', '+', '-', ';', 'div', 'end', 'mod'
```

**CORE-03 — інтерпретатор.** Початкові значення змінних передаються як `ІМ'Я=ЧИСЛО`. Звернення до незаданої змінної та ділення на нуль дають помилку з позицією, а цикл, що крутиться понад 100 000 разів, зупиняється.
```
sipl run examples/factorial.sipl N=5
sipl run examples/gcd.sipl A=48 B=18
```

**CORE-04 — trace.** Інтерпретатор повідомляє про кожен крок: початок і кінець оператора (`BeforeStatement`, `AfterStatement`), зміну змінної (`VariableChanged`), результат умови (`ConditionChecked`), кінець роботи (`Finished`) або помилку (`Failed`).
```
sipl trace examples/power.sipl X=3 Y=1
sipl trace examples/power.sipl X=3 Y=1 --json
```

**CORE-05 — командний рядок.** Шість команд: `check`, `parse`, `run`, `trace`, `tree`, `compare`. З `--json` будь-яка з них друкує один JSON-об'єкт, тож її зручно викликати з іншої програми. Код завершення показує результат:

| Код | Коли |
|---|---|
| 0 | усе добре |
| 1 | синтаксична помилка |
| 2 | немає файлу або неправильні аргументи |
| 3 | помилка під час виконання |

Усі опції та формат JSON: [docs/cli.md](docs/cli.md).

**CORE-06 — conformance suite.** 27 JSON-файлів: програма плюс очікуваний AST, стан або помилка. Скрипт `run.py` не імпортує наш код, а запускає вказану команду й порівнює її JSON, тому так само можна перевірити реалізацію SIPL іншою мовою.
```
python conformance/run.py sipl
```
Очікується `27/27 passed`. Як влаштовані тести: [conformance/README.md](conformance/README.md).

**VIS-01 — дерево виводу.** Показує, як програма виводиться з граматики: усі нетермінали (`<stmt>`, `<aexpr>` …) і всі термінали (`begin`, `;`, `:=`). Кожен вузол знає свій фрагмент коду.
```
sipl tree examples/gcd.sipl
sipl tree examples/gcd.sipl --format svg -o gcd.svg
sipl tree examples/gcd.sipl --format dot -o gcd.dot
```

**VIS-02 — порівняння з AST.** HTML-сторінка з двома деревами однієї програми: зверху дерево виводу, знизу AST, і таблиця з кількістю вузлів. Якщо навести мишку на вузол AST, підсвічується частина дерева виводу, з якої він утворився.
```
sipl compare examples/gcd.sipl -o gcd.html
```
Подробиці про обидві візуалізації: [docs/visualization.md](docs/visualization.md).

## Від тексту до результату

```
power.sipl ──Lark + sipl.lark──► дерево Lark ──parser.py──► AST ──interpreter──► стан + події
                                      │                       │                       │
                                      ▼                       ▼                       ▼
                               sipl tree (VIS-01)    sipl compare (VIS-02)    sipl run / trace
```

Шари не залежать від наступних: інтерпретатор отримує готовий AST і нічого не знає про Lark, а команди `sipl` лише викликають ті самі функції `parse` і `run`.

## Автоматична перевірка

```
pytest
```

Запускає 238 перевірок і рахує покриття коду тестами (зараз 99 %, мінімум — 80 %). Один файл тестів запускається з `--no-cov`, інакше pytest рахує покриття лише за ним і повідомляє про недостатнє покриття.

## Карта репозиторію

```
src/sipl/grammar/       sipl.lark — граматика
src/sipl/ast.py         вузли AST і SourceSpan
src/sipl/parser.py      текст → AST
src/sipl/interpreter/   виконання і події trace
src/sipl/visualization/ дерево виводу, SVG, DOT, HTML
src/sipl/cli.py         команда sipl
conformance/            еталонні тести і run.py
examples/               програми для запуску
tests/                  pytest
docs/                   граматика, CLI, візуалізація
```

## Чого тут немає

* Розширень мови понад БНФ практикуму, крім `div` і `mod`: немає `<`, `and`, логічних констант, коментарів, мінуса перед змінною.
* Дробових чисел. `div` і `mod` округлюють униз, як `//` і `%` у Python
* Точного виявлення нескінченних циклів: замість цього діє ліміт ітерацій, який можна змінити через `--max-iterations`.
