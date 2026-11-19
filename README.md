# CS 182 Project Phase 2

## Project Structure
- `src/fuzz.py`: A coverage-guided fuzzer for Python programs using `coverage`.
- `run_tests.py`: Runs the three checks (fixed-input tests, bug-finding tests, random testing baseline).
- `requirements.txt`: Required packages.
- `.github/programs/`: The 8 target programs.
- `.github/fixed_inputs/`: 5 seed corpora per program (20 inputs each).
- `.github/fixed_expected/`: Expected output of running each seed corpus with `--budget 0`.
- `.github/campaign_seeds/`: The initial seed corpus of each program's campaigns.
- `.github/campaign_expected/`: The exception signatures each program's campaign should find.
- `.github/workflows/`: GitHub Actions workflow that runs the three checks on every push.

## Setup
```bash
pip install -r requirements.txt
```

## How to Run
```bash
python3 src/fuzz.py <program_path> <seeds_dir> [--budget N] [--seed S] [--random]
```
Runs one fuzzing campaign. It runs every seed in `<seeds_dir>` (in order of file names), then `N` new inputs (default 15000). New inputs are made by mutating a random input of the corpus, or by random generation if `--random` is given. `--seed S` sets the random numbers (default 0), so the same arguments give the same output.

It prints a `NEW` line for each input that covers a new statement, an `EXCEPTION` line for each new exception, and a `DONE` summary at the end.

## How to Run the Tests
```bash
python3 run_tests.py
```
Other options:
```bash
python3 run_tests.py fixed    # only the fixed-input tests
python3 run_tests.py bugs     # only the bug-finding tests
python3 run_tests.py random   # only the random testing baseline
```
Each check prints the command it runs, `[PASS]` or `[FAIL]` for each test, and the total, passed and failed counts. The script exits with a non-zero status if any test fails.
