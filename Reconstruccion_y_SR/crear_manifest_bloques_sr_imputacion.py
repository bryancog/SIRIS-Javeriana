#!/usr/bin/env python3
from pathlib import Path

out=Path("outputs_piloto_sr_then_imputed")
out.mkdir(exist_ok=True)

block=256
size=2048

with open(out/"manifest_blocks.tsv","w") as f:
    task=0
    for r0 in range(0,size,block):
        for c0 in range(0,size,block):
            f.write(f"{task}\t{r0}\t{c0}\t{block}\n")
            task+=1

print("bloques:", task)
print("manifest:", out/"manifest_blocks.tsv")
