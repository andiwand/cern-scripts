"""Read plain or compressed validation CSV/TSV outputs."""
import csv
import gzip
from pathlib import Path

def rows(path, delimiter=','):
    path=Path(path)
    if not path.exists():
        path=path.with_name(path.name+'.gz')
    with gzip.open(path,'rt') if path.suffix=='.gz' else path.open() as stream:
        yield from csv.DictReader(stream,delimiter=delimiter)
