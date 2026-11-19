# Coverage-guided fuzzer
# python3 src/fuzz.py <program_path> <seeds_dir> [--budget N] [--seed S] [--random]

import argparse
import contextlib
import io
import os
import random
import string
import sys

import coverage

parser = argparse.ArgumentParser()
parser.add_argument("program_path")
parser.add_argument("seeds_dir")
parser.add_argument("--budget", type=int, default=15000)
parser.add_argument("--seed", type=int, default=0)
parser.add_argument("--random", action="store_true")
args = parser.parse_args()

program_path = os.path.abspath(args.program_path)
rng = random.Random(args.seed)
CHARS = string.ascii_letters + string.digits
BOUNDARY = [0, 1, -1, 2, 10, 100, 1000, -1000]

with open(program_path, encoding="utf-8") as f:
    source = f.read()

# the first line declares the input type
input_type = ""
first_line = source.split("\n")[0].strip()
if first_line.startswith("# input:"):
    input_type = first_line[len("# input:"):].strip()

code = compile(source, program_path, "exec")
cov = coverage.Coverage(data_file=None, include=[program_path])


# an input is a list of tokens, they are the arguments of the program
def random_int():
    return rng.randint(-1000000, 1000000)


def random_input():
    if input_type == "int":
        return [str(random_int())]
    if input_type == "str":
        length = rng.randint(1, 10)
        return ["".join(rng.choice(CHARS) for _ in range(length))]
    if input_type == "ints":
        length = rng.randint(1, 10)
        return [str(random_int()) for _ in range(length)]
    return []


def mutate_int(n):
    op = rng.randint(1, 5)
    if op == 1:
        return n + rng.choice([-1, 1]) * rng.randint(1, 16)
    if op == 2:
        return -n
    if op == 3:
        return rng.choice(BOUNDARY)
    if op == 4:
        digits = list(str(abs(n)))
        digits[rng.randrange(len(digits))] = str(rng.randint(0, 9))
        value = int("".join(digits))
        if n < 0:
            value = -value
        return value
    return random_int()


def to_int(token):
    try:
        return int(token)
    except ValueError:
        return random_int()


def mutate_str(s):
    op = rng.randint(1, 3)
    # an empty string can only grow
    if len(s) == 0:
        op = 2
    if op == 1:
        i = rng.randrange(len(s))
        return s[:i] + rng.choice(CHARS) + s[i + 1:]
    if op == 2:
        i = rng.randint(0, len(s))
        return s[:i] + rng.choice(CHARS) + s[i:]
    i = rng.randrange(len(s))
    return s[:i] + s[i + 1:]


def mutate_ints(tokens):
    tokens = list(tokens)
    op = rng.randint(1, 4)
    # an empty array can only grow
    if len(tokens) == 0:
        op = 2
    if op == 1:
        i = rng.randrange(len(tokens))
        tokens[i] = str(mutate_int(to_int(tokens[i])))
    elif op == 2:
        tokens.insert(rng.randint(0, len(tokens)), str(random_int()))
    elif op == 3:
        tokens.pop(rng.randrange(len(tokens)))
    elif len(tokens) >= 2:
        i = rng.randrange(len(tokens))
        j = rng.randrange(len(tokens))
        tokens[i], tokens[j] = tokens[j], tokens[i]
    return tokens


def mutate_once(tokens):
    if input_type == "int":
        if len(tokens) == 0:
            return [str(random_int())]
        return [str(mutate_int(to_int(tokens[0])))]
    if input_type == "str":
        s = mutate_str(tokens[0] if len(tokens) > 0 else "")
        if s == "":
            return []
        return [s]
    if input_type == "ints":
        return mutate_ints(tokens)
    return []


def mutate(tokens):
    for _ in range(rng.randint(1, 3)):
        tokens = mutate_once(tokens)
    return tokens


def run(tokens):
    # runs the program once, returns the exception signature (or None) and the lines covered
    sys.argv = [program_path] + tokens
    signature = None
    cov.erase()
    cov.start()
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            exec(code, {"__name__": "__main__", "__file__": program_path})
    except SystemExit:
        pass
    except Exception as e:
        # the last frame in the program file is where it was raised
        line = 0
        tb = e.__traceback__
        while tb is not None:
            if tb.tb_frame.f_code.co_filename == program_path:
                line = tb.tb_lineno
            tb = tb.tb_next
        signature = type(e).__name__ + " at line " + str(line)
    cov.stop()
    result = cov.analysis2(program_path)
    covered = set(result[1]) - set(result[3])
    return signature, covered


covered_lines = set()
exceptions = set()
corpus = []
count = 0


def execute(tokens):
    global count
    count += 1
    signature, covered = run(tokens)
    new_lines = not covered.issubset(covered_lines)
    covered_lines.update(covered)
    text = " ".join(tokens)
    if signature is not None:
        if signature not in exceptions:
            exceptions.add(signature)
            print("Execution " + str(count) + ": EXCEPTION " + signature + " input=" + text)
    elif new_lines:
        corpus.append(tokens)
        print("Execution " + str(count) + ": NEW #lines=" + str(len(covered_lines)) + " input=" + text)


# run the seeds in order of file names
for name in sorted(os.listdir(args.seeds_dir)):
    if name.endswith(".txt"):
        with open(os.path.join(args.seeds_dir, name), encoding="utf-8") as f:
            execute(f.read().split())

# run the new inputs
for _ in range(args.budget):
    if args.random or len(corpus) == 0:
        tokens = random_input()
    else:
        tokens = mutate(rng.choice(corpus))
    execute(tokens)

print("DONE #executions=" + str(count) + " #corpus_inputs=" + str(len(corpus)) +
      " #lines=" + str(len(covered_lines)) + " #exceptions=" + str(len(exceptions)))
