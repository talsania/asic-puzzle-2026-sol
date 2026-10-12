import json, re, subprocess, collections
import networkx as nx

D = json.load(open("puzzle_netlist.json")); cells = D["cells"]
OUT = {"X", "Y", "Q", "HI", "LO"}; FL = {"dfrtp", "dfstp", "dfxtp"}
base = lambda c: re.sub(r"_\d+$", "", c)
byid = {c["id"]: c for c in cells}
drv = {n: c for c in cells for k, n in c["pins"].items() if k in OUT}
flops = [c for c in cells if base(c["cell"]) in FL]

def srcflops(net):
    fl, seen, st = set(), set(), [net]
    while st:
        n = st.pop()
        if n in seen: continue
        seen.add(n); c = drv.get(n)
        if c is None: continue
        b = base(c["cell"])
        if b in FL: fl.add(c["id"]); continue
        if b == "conb": continue
        st.extend(m for k, m in c["pins"].items() if k not in OUT)
    return fl

G = nx.DiGraph(); G.add_nodes_from(f["id"] for f in flops)
for f in flops:
    for s in srcflops(f["pins"]["D"]): G.add_edge(s, f["id"])
sccs = [sorted(s) for s in nx.strongly_connected_components(G)]

cnt9 = [s for s in sccs if len(s) == 9][0]
cntB = [446, 444, 442, 440, 453, 452, 454, 447]
chainC = [391, 371, 389, 363, 385, 360, 396, 386, 387, 383, 381, 382]
pairs = [s for s in sccs if len(s) == 2 and sum(byid[i]["x"] for i in s) / 2 > 100000]
used = set(cnt9) | set(cntB) | set(chainC) | {i for p in pairs for i in p}
misc = sorted(f["id"] for f in flops if f["id"] not in used)
order = cnt9 + cntB + chainC + [i for p in pairs for i in p] + misc
pos = {fid: 2 + k for k, fid in enumerate(order)}      # +2: I, enable first
print("groups: cnt9", len(cnt9), "cntB", len(cntB), "chainC", len(chainC),
      "pairs", len(pairs), "misc", len(misc), "->", len(order), "flops")
print("misc ids:", misc)

# ---- testbench: print I, enable and every flop Q at each posedge ----
tb = open("tb_replay.v").read()
sig = ", ".join(f"dut.{byid[i]['pins']['Q']}" for i in order)
tb = re.sub(r"always @\(posedge clk\) begin.*?end\n",
            'always @(posedge clk) begin #1 $display("%0d %b", $time, {I, enable, ' + sig + '}); end\n',
            tb, flags=re.S)
open("tb_probe.v", "w").write(tb)
subprocess.run(["iverilog", "-o", "probe.vvp", "tb_probe.v", "puzzle_netlist.v"], check=True)
out = subprocess.run(["vvp", "probe.vvp"], capture_output=True, text=True).stdout
rows = []
for l in out.splitlines():
    p = l.split()
    if len(p) == 2 and p[0].isdigit(): rows.append((int(p[0]), p[1]))
print("rows:", len(rows))

def toggles(fid):
    k = pos[fid]; s = [r[1][k] for r in rows]
    return sum(1 for a, b in zip(s, s[1:]) if a != b and "x" not in a + b)

def lsb_first(ids): return sorted(ids, key=lambda i: -toggles(i))
o9, oB = lsb_first(cnt9), lsb_first(cntB)
print("cnt9 toggles:", [toggles(i) for i in o9], " order", o9)
print("cntB toggles:", [toggles(i) for i in oB], " order", oB)

def val(bits, ids):
    s = "".join(bits[pos[i]] for i in reversed(ids))
    return int(s, 2) if set(s) <= {"0", "1"} else -1

def show(c):
    t, bits = rows[c]
    ch = "".join(bits[pos[i]] for i in chainC)
    pr = "".join(str(int(bits[pos[p[0]]]) * 2 + int(bits[pos[p[1]]])) if set(bits[pos[p[0]]] + bits[pos[p[1]]]) <= {"0", "1"} else "x" for p in pairs)
    ms = "".join(bits[pos[i]] for i in misc)
    print(f"{c:3d} I={bits[0]} en={bits[1]} c9={val(bits,o9):4d} cB={val(bits,oB):4d} C={ch} P={pr} M={ms}")

print("\ncycle table (index = posedge number; I/en shown are values just before the edge):")
for c in list(range(0, 46)) + list(range(118, 132)) + list(range(155, 172)):
    if c < len(rows): show(c)
