import csv
import os
import re
from collections import defaultdict
from sys import argv

from isdleda.utils.paths import OUT_DIR, OUT_FILES_PART_FMT

OUT_FILES_CAT_DIR: str = os.path.join(OUT_DIR, "CAT")
OUT_FILES_CAT_FMT: str = os.path.join(OUT_FILES_CAT_DIR, OUT_FILES_PART_FMT)


# Function to parse the lgratio values from the string
def parse_lgratio(line):
    # Find the lgratio array, which is in the form [value1,value2]
    mmatch = re.search(r'lgratio \[([^\]]+)\]', line)
    if mmatch:
        lgratio_str = mmatch.group(1)
        lgratio_values = [float(x) for x in lgratio_str.split(',')]
        return min(
            lgratio_values)  # Return the minimum of the two lgratio values
    return None




# Function to read and process the CSV file
def process_csv(input_file):
    # Store the grouped lines by (N, K, W)
    groups = defaultdict(list)

    # Read the CSV file
    with open(input_file, 'r') as file:
        reader = csv.reader(file, delimiter=',')

        for row in reader:
            # Join the row into a single string (assuming the whole line is one entry in the CSV)
            line = ','.join(row)

            # Extract N, K, W from the line using regex
            match = re.search(r'N=(\d+),K=(\d+),W=(\d+)', line)
            if match:
                N, K, W = match.groups()

                # Parse the lgratio value from the line
                lgratio = parse_lgratio(line)

                if lgratio is not None:
                    # Store the line along with the parsed lgratio
                    groups[(N, K, W)].append((lgratio, line))

    # Ensure output directory exists
    os.makedirs(OUT_FILES_CAT_DIR, exist_ok=True)

    # Iterate through each group and write the result to a separate file
    for (N, K, W), entries in groups.items():
        # Find the entry with the minimum lgratio
        min_lgratio_entry, min_lgratio_value = min(entries, key=lambda x: x[0])

        # Define the output file path
        output_file_path = os.path.join(
            OUT_FILES_CAT_FMT.format(n=N, k=K, w=W, ext='txt'))

        with open(output_file_path, 'w', newline='') as outfile:
            # writer = csv.writer(outfile)
            print(str(min_lgratio_entry), file=outfile)
            print(str(min_lgratio_value), file=outfile)
        print(f"Written to '{output_file_path}'.")


def main():
    # Define the input and output file paths
    input_file = argv[1]
    # Process the file
    process_csv(input_file)

    print("Processing complete. Results saved.")


if __name__ == '__main__':
    main()
