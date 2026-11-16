import json
import subprocess
import sys
import tempfile
from pathlib import Path

CASES = Path(__file__).parent / "cases"


def strip_spans(value):
    if isinstance(value, dict):
        return {key: strip_spans(item) for key, item in value.items() if key != "span"}
    if isinstance(value, list):
        return [strip_spans(item) for item in value]
    return value


def check(command, case):
    expect = case["expect"]
    action = "parse" if "ast" in expect else "run"
    state = [f"{name}={value}" for name, value in case.get("input", {}).items()]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "program.sipl"
        path.write_text(case["source"], encoding="utf-8")
        result = subprocess.run(
            [*command, action, str(path), *state, "--json"], capture_output=True, text=True, encoding="utf-8",
        )
    try:
        output = json.loads(result.stdout)
    except ValueError:
        return False, result.stdout + result.stderr
    if "error" in expect:
        error = output.get("error") or {}
        actual = {"error": {key: error.get(key) for key in expect["error"]}}
    elif "ast" in expect:
        actual = {"ast": strip_spans(output.get("ast"))}
    else:
        actual = {"state": output.get("state")}
    return actual == expect, actual


def main(command):
    files = sorted(CASES.glob("*.json"))
    failed = 0
    for file in files:
        case = json.loads(file.read_text(encoding="utf-8"))
        ok, actual = check(command, case)
        print("PASS" if ok else "FAIL", file.stem)
        if not ok:
            failed += 1
            print("  очікувалось:", json.dumps(case["expect"], ensure_ascii=False))
            print("  отримано:   ", json.dumps(actual, ensure_ascii=False))
    print(f"{len(files) - failed}/{len(files)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("використання: python conformance/run.py КОМАНДА [АРГУМЕНТИ...]", file=sys.stderr)
        sys.exit(2)
    try:
        sys.exit(main(sys.argv[1:]))
    except FileNotFoundError:
        print(f"не вдалося запустити команду '{sys.argv[1]}'", file=sys.stderr)
        sys.exit(2)
