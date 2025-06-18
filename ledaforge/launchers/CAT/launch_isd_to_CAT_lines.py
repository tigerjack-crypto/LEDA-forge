"""Auxiliary script.
Given a CSV file containing a list of ISD values, output the same list formatted as CAT expects
"""
from ledaforge.utils.export.export import load_from_json
from sys import argv

# Parse the JSON data

data = load_from_json(argv[1])

# Output the required lines
for entry in data:
    n_value = entry['n']
    k_value = entry['k']
    w_value = entry['w']
    print(f"\'N={n_value},K={k_value},W={w_value}\',")
