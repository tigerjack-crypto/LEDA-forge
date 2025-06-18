"""Simple script to launch the LEDATools work_factor_computation script.
"""
import argparse
import subprocess
import os

from ledaforge.utils.paths import OUT_DIR
# from pathlib import Path

# Algorithms accepted by LT
ALGO_NAMES = {
  "Prange",
  "Lee_Brickell",
  "Leon",
  "Stern",
  "Finiasz_Sendrier",
  "MMT",
  "BJMM",
}

def main():
    parser = argparse.ArgumentParser(
        description="Run work_factor_computation with given parameters.")
    parser.add_argument('--threads',
                        type=int,
                        required=True,
                        help='Number of OMP threads')
    parser.add_argument('--json',
                        type=str,
                        required=True,
                        help='Path to JSON input file')
    parser.add_argument(
        "--include-algos",
        type=str,
        required=True,
        help=
        (f"Comma-separated list of algorithm names to exclude from execution.\n"
         f"Available algorithms that can be excluded: {ALGO_NAMES}.\n"
         ),
        default="")
    args = parser.parse_args()

    env = os.environ.copy()
    env['OMP_NUM_THREADS'] = str(args.threads)

    include_names = [
        name.strip() for name in args.include_algos.split(",")
        if name.strip()
    ]

    for alg in include_names:
        print(alg)
        command = ['work_factor_computation', '--json', args.json,
                   '--algorithms', alg,
                   '--out-dir', os.path.join(OUT_DIR, 'LT') , '--out', alg]
        # print(' '.join(command))
        try:
            res = subprocess.run(command, env=env, check=True, capture_output=True, text=True)
            # Optional: Check stderr even if returncode == 0
            if res.stderr:
                print("Command succeeded, but there were warnings/errors in stderr:")
                print(res.stderr)
        except subprocess.CalledProcessError as e:
            print("Command failed:")
            print("Return code:", e.returncode)
            print("Standard error:")
            print(e.stderr)
            print("Standard output:")
            print(e.stdout)

if __name__ == '__main__':
    main()
