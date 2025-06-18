# LEDA Parameter Generation and ISD Evaluation Framework

## Aim and Scope

This project provides a parameter set for the cryptosystem called **LEDA**,
leveraging different tools to assess the **Information Set Decoding (ISD)**
attack complexity. It supports:

- Automated generation and filtering of LEDA parameter sets.
- Evaluation of ISD hardness across various classical and quantum attack
  strategies.
- Integration with SoA cryptographic hardness estimators.
- Filtering of viable parameters based on concrete security thresholds (e.g.,
  NIST levels).

The overall goal is to guide the selection of secure and efficient LEDA
instances for use in post-quantum cryptographic applications.

## Organization

- `ledaforge.launchers.CE`: CryptographicEstimators for ISD cost estimation (field
  operations, different memory models).
- `ledaforge.launchers.LT`: LEDAtools for classical (bit-operations, logarithmic
  memory) and quantum decoding (gate-based, no QRAM).
- `ledaforge.launchers.CAT`: CryptAttackTester for additional ISD complexities
  (bit-level, combinatorial circuit unrolling).
- `ledaforge.launchers.orchestra.*`: Orchestrators for coordinating generation and conversion.

## ISD LEDA Values Generation Steps

### Stage 0

- Generate an exhaustive list of LEDA parameter values in CSV format `<n0, p, v, t>`
  using `ledaforge.launchers.orchestra.launch_values_generation`.

### Stage $i > 0$
- For each LEDA value coming from the previous stage, derive the ISD parameter
  sets (note that there are 4 ISD attack parameter for each LEDA value) in JSON
  format `<n, k, w>` using
  `ledaforge.launchers.orchestra.launch_leda_to_isd_converter`. Ex.
  ```bash

  ```
- Compute ISD complexities using external tools (see [Tools](#ISD-Tools)
- Merge previous-stage LEDA values with estimates of their computational
  complexity `ledaforge.launchers.orchestra.launch_leda_to_attack_merger`. The
  script additionally apply reduction models (e.g., DOOM) and filter for values
  where cost $\geq c \lambda$, where $\lambda$ is a threshold security level, and $c$ a threshold percentage.
  The lambda values, as specified or derived from NIST, are
  - Classical: 143, 207, 272
  - Quantum: 154, 219, 283
  An example usage is
  ```bash
  python3 -m ledaforge.launchers.orchestra.launch_leda_to_attack_merger 1 ../leda_design/stime_ISD/out/orchestra/values/S0/exhaustive_generation/ ../leda_design/stime_ISD/out/LT/Stern LT 1
  ```
- Perform a Decoding Failure Rate (DFR) analysis on filtered results using
  external tools, and output a new set of LEDA values.

# ISD Tools
The tools used to estimate the computational complexity of ISD attack parameters
are kept as submodules of this project (inside `./submodules` directory). To
initialize all submodules, you should use
`git submodule update --init --recursive`

This section provides descriptions and usage details for the tools integrated
into the workflow.

Each tool outputs a list of files named as `{n:06}_{k:06}_{w:03}` in a specific
folder. Check `ledaforge.utils.paths` for further info.

## Cryptographic Estimators (CE):
Original tool, developed by TII, can be found
[here](https://github.com/Crypto-TII/CryptographicEstimators). The custom
launcher can be run using `ledaforge.launchers.CE.launch_CE`. An example run is

```bash
LOG_LEVEL=error python3 -m ledaforge.launchers.CE.launch_CE --poolsize 64 --max-tasks 1 --chunksize 1 --out-format json --input $MDIR_LINUX_DATA/vc/leda_design/stime_ISD/out/orchestra/values/S3/2_leda2isd/isd_values.json --excluded-algos=Dumer,Stern,BJMM
```

## LEDATools (LT)
LEDAtools for classical and quantum decoding.
Original tool (rebirth branch) [here](https://github.com/tigerjack-crypto/LEDAtools/tree/rebirth).
Before using the tools, compile the project.

```bash
cd ./submodules/LEDATools/
mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=.. ..
make install -j
```

Then, you can run the custom launcher script `ledaforge.launchers.LT.launch_LT`.
An example run is:

```bash
python3 -m ledaforge.launchers.LT.launch_LT --threads 2 --json "$MDIR_LINUX_DATA"/vc/crypto/leda_design/stime_ISD/out/orchestra/values/S2/isd_values.json --include-algos Stern,BJMM
```

## CryptAttackTester
The CryptAttackTester (CAT) source code can be retrieved from one of the original
authors blog, that I report here for simplicity
[link](https://cat.cr.yp.to/cryptattacktester-20231020.tar.gz).
To add it to your local project, use
```bash
wget https://cat.cr.yp.to/cryptattacktester-20231020.tar.gz
tar -xf cryptattacktester-20231020.tar.gz -C submodules
rm cryptattacktester-20231020.tar.gz
```

Since the original source code requires compilation, you need to generate the binaries from the submodule.
```bash
cd ./submodules/cryptattacktester-20231020/
make -j
```

The script launcher `ledaforge.launchers.CAT.launch_CAT_isdpredict`, heavily based
on the `isdpredict1.py` script provided by the CAT authors, can then be used to
generate the ISD estimates.


Example usage:
```bash
python3 -m ledaforge.launchers.CAT.launch_CAT_isdpredict --isd_csv ledaforge/launchers/CAT/isd_leda.csv --start 62 --end 63 --isd_level 2 --processes 12 --add_hostname
```

Note: This tool is resource-intensive at higher ISD levels. To run it on
multiple servers, use the `--add_hostname` flag to write results to separate
subdirectories, and easily copy them on a unique machine for post-processing. To
aggregate the outputs (as this is the way in which the authors intended it to be
used) you can then run

```bash
cat {server1,server2,server3}/* > all.out
```

Then, to process the final merged output, and put each ISD value in a separate
file together with its best attack, execute

```bash
python3 -m ledaforge.launchers.launch_cat_out_processer all.out 2
```


# DFR Tools
Internal repo, to be specified
