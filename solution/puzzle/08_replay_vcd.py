import re, subprocess

# ---- parse VCD ----
ids, ev, t = {}, [], 0
for line in open("example_inputs.vcd"):
    line = line.strip()
    if line.startswith("$var"):
        p = line.split(); ids[p[3]] = p[4]; continue
    if line.startswith("#"): t = int(line[1:]); continue
    if not line or line[0] == "$": continue
    if line[0] == "b":
        v, i = line[1:].split()
        if i in ids: ev.append((t, ids[i], v))
    elif line[0] in "01xz" and line[1:] in ids:
        ev.append((t, ids[line[1:]], line[0]))

def pad8(v):
    return v.rjust(8, "0" if v[0] in "01" else v[0])

# ---- testbench replaying clk/rst_n/enable/I exactly ----
tb = ["`timescale 1ps/1ps", "module tb;", "reg clk, rst_n, enable, I;",
      "wire [7:0] O; wire success;",
      "puzzle dut(.clk(clk),.rst_n(rst_n),.I(I),.enable(enable),.O(O),.success(success));",
      'always @(posedge clk) begin #1 $display("%0d %b %b", $time, O, success); end',
      "initial begin"]
last = 0
for tt, n, v in ev:
    if n in ("clk", "rst_n", "enable", "I"):
        if tt > last: tb.append(f"#{tt-last};"); last = tt
        tb.append(f"{n} = 1'b{v};")
tb += ["#20000;", "$finish;", "end", "endmodule"]
open("tb_replay.v", "w").write("\n".join(tb))

def vcd_at(name, tq):
    val = "x"
    for tt, n, v in ev:
        if n == name and tt <= tq: val = v
    return pad8(val) if name == "O" else val

base = open("puzzle_netlist.v").read()
for tie in [None, "0", "1"]:
    src = base if tie is None else base.replace(
        "endmodule", f"  assign n589 = 1'b{tie};\nendmodule")
    open("puzzle_try.v", "w").write(src)
    subprocess.run(["iverilog", "-o", "replay.vvp", "tb_replay.v", "puzzle_try.v"], check=True)
    out = subprocess.run(["vvp", "replay.vvp"], capture_output=True, text=True).stdout
    bad, total, distinct = [], 0, set()
    for l in out.splitlines():
        p = l.split()
        if len(p) != 3 or not p[0].isdigit(): continue
        tq = int(p[0]); total += 1
        eo, es = vcd_at("O", tq), vcd_at("success", tq)
        distinct.add(eo)
        if (p[1], p[2]) != (eo, es): bad.append((tq, p[1], p[2], eo, es))
    print(f"n589 tie={tie}: {total} cycles, {len(bad)} mismatches, "
          f"{len(distinct)} distinct O values in VCD")
    for b in bad[:4]: print("   t=%d  got O=%s s=%s  expected O=%s s=%s" % b)
