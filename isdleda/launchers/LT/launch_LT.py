"""Simple script to launch the LEDATools work_factor_computation script.
As an example, the script can be launched as

--threads 32 --json ../leda_design/stime_ISD/isd-leda/values/S3/2_leda2isd/isd_values.json --out BJMM

"""
import argparse
import subprocess
import os
from pathlib import Path


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
    parser.add_argument('--out',
                        type=str,
                        required=True,
                        help='Output file name')
    parser.add_argument('--bin-dir',
                        type=str,
                        required=True,
                        help='Path to the directory containing the bins')
    args = parser.parse_args()

    env = os.environ.copy()
    env['OMP_NUM_THREADS'] = str(args.threads)

    # Define the path to the executable relative to this script
    exec_path = Path(
        __file__).parent.resolve() / '../A/B/C/bin/work_factor_computation'
    exec_path = exec_path.resolve()  # resolve to absolute path

    if not exec_path.exists():
        raise FileNotFoundError(f"Executable not found at {exec_path}")

    command = [str(exec_path), '--json', args.json, '--out', args.out]

    subprocess.run(command, env=env, check=True)


if __name__ == '__main__':
    main()
