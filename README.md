# World News in One Image — Wednesday, 18 November 2026

Entry for the make.fun bounty
[Sum up 18 November's world news in one image](https://make.fun/bounty/news-image-20261118)
($250 prize pool, 50 places paid).

`main.py` is a self-contained Python 3.13 program (standard library only —
`zlib`/`struct`/`os`) that draws a 1024×1024 PNG newspaper poster of the
day's 7 top stories and writes it to `/output/entry.png` (plus a preview
copy at `output/entry.png` next to the script).

## How it works

No image libraries exist in the stdlib, so the program includes:

- a hand-written PNG encoder (IHDR/IDAT/IEND chunks, zlib level 9),
- an embedded 5×7 bitmap font (full ASCII) rendered at 2×–6× scale,
- a fixed layout: masthead + date, one row per story with a colour-coded
  category chip (red = conflict, blue = diplomacy, green = economy,
  orange = defence), bold headline and one-line summary.

## Run

```sh
python3 main.py
```

## Determinism

The program uses no network, no clock and no randomness. Running it twice
produces byte-identical PNG output (verified with sha256).

## Stories covered

The APEC Summit opening in Shenzhen, Trump in Manila for QUAD talks, the
first-ever Trump–Xi–Putin trilateral summit, Ukraine hitting the Crimean
Bridge a second day, Iranian drones targeting the US radar in Bahrain, the
Gaza ceasefire warning, and Nvidia doubling quarterly revenue to $115.84B.

## License

MIT — see `LICENSE`.
