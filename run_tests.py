# python run_tests.py            runs all three checks
# python run_tests.py fixed      Fixed-input tests
# python run_tests.py bugs       Bug-finding tests
# python run_tests.py random     Random testing baseline

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

here = os.path.dirname(os.path.abspath(__file__))
data = os.path.join(here, ".github")

choice = ""
if len(sys.argv) > 1:
    choice = sys.argv[1]

any_failed = False


def program_names():
    names = []
    for filename in sorted(os.listdir(os.path.join(data, "programs"))):
        if filename.endswith(".py"):
            names.append(filename[:-3])
    return names


def fuzz(args):
    # runs the fuzzer, returns the command and the lines it printed
    command = [sys.executable, "src/fuzz.py"] + args
    result = subprocess.run(command, capture_output=True, cwd=here)
    text = result.stdout.decode("utf-8", errors="replace").replace("\r\n", "\n")
    return " ".join(command), text.strip().split("\n"), result.returncode


def print_summary(total, passed, failed):
    print("=" * 30)
    print("TOTAL: " + str(total))
    print("PASSED: " + str(passed))
    print("FAILED: " + str(failed))
    print("=" * 30)


def read_lines(path):
    with open(path, encoding="utf-8") as f:
        return f.read().strip().split("\n")


# Fixed-input tests
def fixed_test(test):
    name, set_name = test
    args = [".github/programs/" + name + ".py",
            ".github/fixed_inputs/" + name + "/" + set_name, "--budget", "0"]
    command, actual, code = fuzz(args)
    expected = read_lines(os.path.join(data, "fixed_expected", name, set_name + ".txt"))
    label = name + ".py / " + set_name
    text = "$ " + command + "\n"
    if code != 0:
        return text + "[FAIL] " + label + ": exit code " + str(code)
    if actual != expected:
        return text + "[FAIL] " + label + ": output mismatch"
    return text + "[PASS] " + label


if choice in ("", "fixed"):
    print("Fixed-input tests")
    tests = []
    for name in program_names():
        for set_name in sorted(os.listdir(os.path.join(data, "fixed_inputs", name))):
            tests.append((name, set_name))

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(fixed_test, tests))

    failed = 0
    for text in results:
        print(text)
        if "[FAIL]" in text:
            failed += 1
    print_summary(len(tests), len(tests) - failed, failed)
    if failed > 0:
        any_failed = True


# one campaign: (program name, seed, extra arguments)
def campaign(job):
    name, seed, extra = job
    args = [".github/programs/" + name + ".py", ".github/campaign_seeds/" + name,
            "--budget", "15000", "--seed", str(seed)] + extra
    return fuzz(args)


def show(prefix, command, lines):
    # prints the command, the EXCEPTION lines and the DONE line
    print(prefix + ": $ " + command)
    for line in lines:
        if "EXCEPTION" in line or line.startswith("DONE"):
            print(prefix + ": " + line)


# Bug-finding tests
if choice in ("", "bugs"):
    print("Bug-finding tests")
    jobs = []
    for name in program_names():
        for seed in range(3):
            jobs.append((name, seed, []))

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(campaign, jobs))

    passed = 0
    failed = 0
    for name in program_names():
        outputs = []
        for i in range(len(jobs)):
            if jobs[i][0] == name:
                command, lines, code = results[i]
                show(name + ".py seed=" + str(jobs[i][1]), command, lines)
                outputs.append("\n".join(lines))

        problems = []
        for signature in read_lines(os.path.join(data, "campaign_expected", name + ".txt")):
            found = 0
            for output in outputs:
                if "EXCEPTION " + signature + " input=" in output:
                    found += 1
            if found >= 2:
                print("[PASS] " + name + ".py: " + signature + " found in " + str(found) + "/3 campaigns")
            else:
                problems.append(signature + " found in " + str(found) + "/3 campaigns")

        if len(problems) > 0:
            print("[FAIL] " + name + ".py: " + "; ".join(problems))
            failed += 1
        else:
            passed += 1

    print_summary(passed + failed, passed, failed)
    if failed > 0:
        any_failed = True


# Random testing baseline
if choice in ("", "random"):
    print("Random testing baseline")
    jobs = []
    for name in program_names():
        jobs.append((name, 0, ["--random"]))

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(campaign, jobs))

    for i in range(len(jobs)):
        command, lines, code = results[i]
        show(jobs[i][0] + ".py random seed=0", command, lines)

if any_failed:
    sys.exit(1)
