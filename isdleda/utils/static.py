import csv
from typing import Tuple
from isdleda.utils.paths import PRIMES_FILE_CSV

@staticmethod
def get_primes() -> Tuple[int, ...]:
   proper_primes = ()
   with open(PRIMES_FILE_CSV, 'r', newline='') as csvfile:
      reader = csv.reader(csvfile)
      for row in reader:
         proper_primes = tuple(map(int, row))

   return proper_primes
