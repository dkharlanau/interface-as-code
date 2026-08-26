from __future__ import annotations
import argparse, tempfile, time
from pathlib import Path
from interface_as_code.scaffold import write_profile
from interface_as_code.catalog import build_catalog

def run(count: int) -> float:
    with tempfile.TemporaryDirectory() as raw:
        root=Path(raw)/"portfolio"
        for n in range(count):write_profile(root/f"i{n:05d}","rest-api",f"BENCH-{n:05d}",f"Benchmark interface {n}",f"SYS-{n%50:02d}",f"SYS-{(n+1)%50:02d}",minimal=True)
        start=time.perf_counter();build_catalog(root,Path(raw)/"catalog");return time.perf_counter()-start

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("counts",nargs="*",type=int,default=[50,500,5000]);args=p.parse_args()
    for count in args.counts:print(f"{count},{run(count):.4f}")
