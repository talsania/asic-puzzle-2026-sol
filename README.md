# Reverse engineering Jane Street's ASIC puzzle (2026)

My solution to [janestreet/asic-puzzle-2026](https://github.com/janestreet/asic-puzzle-2026)
(puzzle by Anish Singhani and Benjamin Devlin). Submissions closed on 4 September 2026.

## What the chip does

The chip reads a 121-bit serial stream on `I`, one bit per clock, as an 11x11 grid in
row-major order. It checks that the grid is a valid **Star Battle** solution with 2 stars:
exactly 2 stars in every row, column and coloured region, and no two stars touching
(diagonals included). The one valid placement raises `success`, which unlocks the
output generator. `O[7:0]` then emits the answer as ASCII.

## Method

1. **Netlist from the GDS.** Cell names and pin labels were intact. I merged each metal
   layer into polygons, joined them through the vias (union-find with a grid index), and
   mapped every pin label to a net. Output: a gate-level Verilog netlist, simulated with
   Icarus Verilog. It reproduces all 312 cycles of `example_inputs.vcd`.
   The `warmup/` folder was used to build and check the extractor first.
2. **Structure.** The graph of 92 flops contains a cycle counter, an 8-bit popcount of the
   input, a delay line, and 22 two-flop slices.
3. **Probing.** Sending a single `1` at each of the 121 positions showed which slices react:
   11 slices follow the columns, the other 11 follow irregular regions. This recovers the
   region map straight from the chip.
4. **Reading the checker.** The `success` flop's D input is a 47-gate AND tree. It needs
   every slice at count 2, the popcount to be 22, and a violation flag to be clear. My first
   guess (Queens, one per line) was wrong: it gave 2727 candidates and none worked.
5. **Solving.** A backtracking search finds exactly one placement. On the chip it holds
   `success` high and `O` spells the answer, then goes to zero.

Not verified: the exact role of the delay line, and of one flag flop (id 412) that must be 0.
They were inferred from the netlist, not proven.

## Easter egg

A row of 36 empty cells below the design (`INTERNAL_3` = dot, `INTERNAL_7` = dash) spells
Morse code: **PER ARENAM AD ASTRA**. The answer string `(* ... *)` is also Verilog
attribute syntax, possibly a nod.

## Answer

```
(* TWO STARS *)
```

## Reproduce

```powershell
pip install -r requirements.txt
# needs iverilog on PATH; get it with: winget install icarus-verilog
git clone https://github.com/janestreet/asic-puzzle-2026
# copy this repo's solution/ folder into the clone, then run from the clone's root:
py solution\puzzle\03_extract_netlist.py
py solution\puzzle\08_replay_vcd.py
py solution\puzzle\12_probe_positions.py
py solution\puzzle\14_solve_star_battle.py
```

Scripts read and write files in the current directory, so always run them from the root
of the clone. Jane Street's input files (`puzzle.gds`, `example_inputs.vcd`, `warmup/`)
are not included here.

## Scripts

| Folder | Script | Purpose |
|---|---|---|
| `solution/warmup` | `01_inspect_gds.py` | list layers and cells of the warmup GDS |
| | `02_extract.py` | first extractor (pin lookup via KLayout) |
| | `03_sim.py` | Python simulator, checks netlist against `00_source.v` |
| `solution/puzzle` | `01_inspect_puzzle.py` | layers, cell types, top-level labels |
| | `02_inspect_internal.py` | the two `INTERNAL_*` cells |
| | `03_extract_netlist.py` | **main extractor**: writes `puzzle_netlist.json` / `.v` |
| | `04_morse_row.py` | Morse row positions |
| | `05_find_undriven.py`, `06_dangling_drivers.py` | netlist sanity checks |
| | `07_parse_vcd.py` | reads the stimulus from the sample VCD |
| | `08_replay_vcd.py` | replays the sample VCD through the netlist (0 mismatches) |
| | `09_structure.py`, `10_structure_scc.py` | flop graph, cones, SCCs |
| | `11_probe_cycles.py` | per-cycle state of every flop group |
| | `12_probe_positions.py` | one-hot probing, finds columns and regions |
| | `13_diagnose_success_tree.py` | prints the `success` logic and slice states |
| | `14_solve_star_battle.py` | **solver**: finds the placement, decodes `O` |
| `solution/attempts` | `solve_queens.py` | failed Queens hypothesis, kept for the record |
| `solution/puzzle` | `smoke_test.v` | hand-written Verilog testbench |

Scripts `08` to `14` depend on files written by earlier ones (see the order above).
