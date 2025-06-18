"""Launch the CAT searchparams utils.
"""
import argparse
import csv
import fcntl
import itertools
import multiprocessing
import os
import resource
import subprocess
import sys
import time
from datetime import datetime

from ledaforge.launchers.CAT.utils.attacks_list import (attacks0, attacks1,
                                                        attacks2)
# from ledaforge.launchers.CAT.utils.file_mgmt import OUT_DIR, OUT_FILE
from ledaforge.utils.common import dict_to_isd_value
from ledaforge.utils.export.export import load_from_json
from ledaforge.utils.paths import OUT_DIR, OUT_FILES_PART_FMT

# Fixed values, stop at 1st iteration
ATTACK_ITERATIONS = 'I=1,RE=1,X=1,YX=1'
OUT_FILE = os.path.join("CAT", "stdout", ("{hostname}"), OUT_FILES_PART_FMT)

# To testify that I tried, and failed, to have consistent unique values to
# avoid redundant computation

# ALREADY_COMPUTED_0A: Set[SearchParamsResult] = set()
# ALREADY_COMPUTED_0: Set[SearchParamsResult] = set()
# ALREADY_COMPUTED_1: Set[SearchParamsResult] = set()
# ALREADY_COMPUTED_2: Set[SearchParamsResult] = set()
# def set_compare_fields(obj: SearchParamsResult):
#     """This sets compare fields of SearchParamsResult dinamically by taking
#     into account the values present in the attack_list file."""
#     match obj.attack:
#         case 'isd0':
#             obj._compare_fields = {'N', 'K', 'W', 'attack', 'problem', 'P', 'FW'}
#         case 'isd1':
#             obj._compare_fields = {'N', 'K', 'W', 'attack', 'problem', 'PI', 'FW'}
#         case 'isd2':
#             obj._compare_fields = {'N', 'K', 'W', 'attack', 'problem', 'PI', 'PIJ', 'CP', 'CS', 'FW'}
#         case _:
#             raise Exception(f"Wrong attack {obj.attack}")
# def load_already_computed(outdir):
#     for filename in os.listdir(outdir):
#         results = load_results_from_csv(os.path.join(outdir, filename))
#         for result in results:
#         ALREADY_COMPUTED.update(results)


def parse_args():

    def parse_isd_levels(value):
        try:
            levels = [int(x) for x in value.strip("()").split(",")]
        except ValueError:
            raise argparse.ArgumentTypeError(
                "ISD levels must be integers separated by commas")

        allowed = {0, 1, 2}
        if not set(levels).issubset(allowed):
            raise argparse.ArgumentTypeError("ISD levels must be 0, 1, or 2")

        return levels

    parser = argparse.ArgumentParser(
        description=
        "Run parallel ISD attack search and store outputs per (n,k,w) group.")
    parser.add_argument("--input",
                        required=True,
                        help="Path to the input CSV containing (n,k,w) rows")
    parser.add_argument("--stop_at_first",
                        action="store_true",
                        help="Stop at the 1st iteration of the ISD attack")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--input_contains_attacks",
        action="store_true",
        help=
        ("If set, the input file is a CSV file (n,k,w,attack), in which attack contains the CAT attack string. "
         "This option cannot be used together with --isd_levels."))
    group.add_argument(
        "--isd_levels",
        type=parse_isd_levels,
        help=
        ("Comma-separated list of ISD attack levels (e.g., 0,1 or (0,1,2)). "
         "This option cannot be used together with --input_contains_attacks."))

    parser.add_argument("--start",
                        type=int,
                        required=True,
                        help="Start index for problems")
    parser.add_argument("--end",
                        type=int,
                        required=True,
                        help="End index for problems (exclusive)")
    parser.add_argument("--processes",
                        type=int,
                        required=True,
                        help="Number of parallel processes")
    parser.add_argument("--add_hostname",
                        action="store_true",
                        help="Add hostname in output filenames")
    return parser.parse_args()


def handle(task):
    command, out_filename = task
    # print(f"[{datetime.now().isoformat(timespec='seconds')}] Starting process w/ command {command_txt}")
    ts = time.time()
    try:
        searchparams = subprocess.run(command,
                                      capture_output=True,
                                      universal_newlines=True,
                                      text=True,
                                      check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error for {command}\n{e.stderr}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Unexpected error for {command}\n{str(e)}", file=sys.stderr)
        return None
    if searchparams.stderr:
        print(f"Warning/Error: {searchparams.stderr}", file=sys.stderr)
        return None
    te = time.time()

    # print(f"[{datetime.now().isoformat(timespec='seconds')}] Finished process w/ command {command_txt}")
    if len(searchparams.stdout.strip()) == 0:
        print(f"len0: {command}", file=sys.stderr)
        return None
    result_line = searchparams.stdout.strip().splitlines()[-1]

    # Useless, it's better to produce the output lines as CAT intended, and
    # post-process later.
    #
    # result = parse_searchparams_line(result_line)
    # append_result_to_csv(result, out_filename, should_lock=True)

    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    # expressed in KiB
    max_rss_kb = usage.ru_maxrss
    # Convert to GiB
    max_rss_gb = max_rss_kb / (1 << 20)
    with open(out_filename, 'a') as f:
        # Atomic file append with locking
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(result_line + f" seconds={te - ts} memory_giga={max_rss_gb}"
                '\n')
        fcntl.flock(f, fcntl.LOCK_UN)

    return result_line


# def is_already_computed(filename, content):
#     if os.path.exists(filename):
#         parsed = parse_searchparams_line(content)
#         is_computed = parsed in ALREADY_COMPUTED
#         if is_computed:
#             print(f"{filename} already computed for {content}")
#         return is_computed
#         # print(f"{filename} exists")
#         # print(f"checking for content {content}")
#         # with open(filename, 'r') as f:
#         #     for existing_line in f:
#         #         match_content = existing_line.split("lgratio")[0].strip()
#         #         print(f"current line to match {match_content}")
#         #         if match_content.find(content) > 0:
#         #             print(f"{filename} found duplicate")
#         #             return True  # Duplicate found, skip writing
#     # return False


def get_command_content(problem, attack, attack_iterations):
    p_to_txt = f"N={problem['n']},K={problem['k']},W={problem['w']}"
    command = [
        'searchparams',
        'problem=uniformmatrix',
        p_to_txt,
        attack,
        attack_iterations,
    ]
    command_txt = ' '.join([command[0].removeprefix('./')] + command[1:])
    # line_content = p_to_txt + " " + attack + " " + command_txt
    return command, command_txt


def main():
    args = parse_args()

    problems_all = []

    if args.input_contains_attacks:
        with open(args.input) as csvfile:
            reader = csv.DictReader(csvfile)
            # Read each row from the CSV file
            for row in reader:
                # Extract values and append to the items list
                n = int(row['n'])  # Assuming 'n' is an integer
                k = int(row['k'])  # Assuming 'k' is an integer
                w = int(row['w'])  # Assuming 'w' is an integer
                attack = row['attack']
            problems_all.append({'n': n, 'k': k, 'w': w, 'attack': attack})
    else:
        for json_value in load_from_json(args.input):
            isd_value = dict_to_isd_value(json_value)
            problems_all.append({
                'n': isd_value.n,
                'k': isd_value.k,
                'w': isd_value.w,
                'attack': None
            })

    len_all = len(problems_all)
    print(f"{len_all} unique candidate ISD values")

    start, end = args.start, args.end
    if start < 0:
        print("Warning, start was below 0")
        start = 0
    if end >= len_all:
        print(f"Warning, end was above max, bringing to {len_all}",
              file=sys.stderr)
        end = len_all
    print(f"Range {start}:{end}", file=sys.stderr)

    hostname = os.uname()[1] if args.add_hostname else "."
    os.makedirs(OUT_DIR.format(hostname=hostname), exist_ok=True)

    commands = []
    if args.isd_levels is not None:
        attacks = [tuple()] * 3
        for level in args.isd_levels:
            match level:
                case 0:
                    print(f"Adding {len(attacks0)} attacks")
                    attacks[0] = attacks0
                case 1:
                    print(f"Adding {len(attacks1)} attacks")
                    attacks[1] = attacks1
                case 2:
                    print(f"Adding {len(attacks2)} attacks")
                    attacks[2] = attacks2
                case _:
                    raise Exception(f"Unrecognized attack {level}")
        attacks = list(itertools.chain(*attacks))
        print(f"Selected isd {args.isd_levels} having {len(attacks)} attacks")
        for problem, attack in itertools.product(problems_all[start:end],
                                                 attacks):
            filename = OUT_FILE.format(hostname=hostname,
                                       n=problem['n'],
                                       k=problem['k'],
                                       w=problem['w'],
                                       ext='out')
            # _ is the line_content
            command, _ = get_command_content(problem, attack,
                                             ATTACK_ITERATIONS)
            # if not is_already_computed(filename, line_content):
            commands.append((command, filename))
    else:
        # the attack is already in the csv file
        for problem in problems_all[start:end]:
            filename = OUT_FILE.format(hostname=hostname,
                                       n=problem['n'],
                                       k=problem['k'],
                                       w=problem['w'],
                                       ext='out')
            command, _ = get_command_content(problem, problem['attack'],
                                             ATTACK_ITERATIONS)
            commands.append((command, filename))
    # load_already_computed(OUT_DIR.format(hostname=hostname))

    print(f"{len(commands)} commands to spawn")

    print(
        f"[{datetime.now().isoformat(timespec='seconds')}] Spawning processes")
    with multiprocessing.Pool(processes=args.processes) as pool:
        total = len(commands)
        completed = 0
        for result in pool.imap_unordered(handle, commands, chunksize=1):
            completed += 1
            percent = (completed / total) * 100
            print(f"\rProgress: {completed}/{total} ({percent:.1f}%)",
                  end='',
                  flush=True)
            # You can skip this if you only care about files
            if result is not None:
                pass  # or log to a central summary file if needed
        print()

    print(
        f"[{datetime.now().isoformat(timespec='seconds')}] All computations over"
    )


if __name__ == '__main__':
    main()
