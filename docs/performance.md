# Portfolio performance baseline

Run:

```bash
PYTHONPATH=src python scripts/benchmark.py 50 500 5000
```

Reference development-container run on 2026-08-26:

| Specs | Catalog build |
| ---: | ---: |
| 50 | 0.17 s |
| 500 | 1.73 s |
| 5,000 | 15.56 s |

These are regression baselines, not hardware-independent promises. The target is predictable roughly linear portfolio builds and a reproducible 5,000-spec scale check.
