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
sccs = sorted(sorted(s) for s in nx.strongly_connected_components(G))
pairs = [s for s in sccs if len(s) == 2 and sum(byid[i]["x"] for i in s) / 2 > 100000]
print("slices:", len(pairs))
json.dump(pairs, open("pairs.json", "w"))
Q = lambda i: "dut." + byid[i]["pins"]["Q"]
cat = ", ".join(Q(i) for p in pairs for i in p)

tb = f"""`timescale 1ns/1ps
module tb;
reg clk=0, rst_n=0, I=0, enable=0;
wire [7:0] O; wire success;
puzzle dut(.clk(clk),.rst_n(rst_n),.I(I),.enable(enable),.O(O),.success(success));
always #5 clk = ~clk;
integer k, t;
task run(input integer kk);
begin
  rst_n=0; enable=0; I=0;
  repeat(3) @(negedge clk);
  rst_n=1; @(negedge clk);
  enable=1;
  for (t=0; t<121; t=t+1) begin I=(t==kk); @(negedge clk); end
  $display("%0d %b", kk, {{{cat}}});
end
endtask
initial begin
  run(-1);
  for (k=0; k<121; k=k+1) run(k);
  $finish;
end
endmodule
"""
open("tb_exp.v", "w").write(tb)
subprocess.run(["iverilog", "-o", "exp.vvp", "tb_exp.v", "puzzle_netlist.v"], check=True)
out = subprocess.run(["vvp", "exp.vvp"], capture_output=True, text=True).stdout
res = {}
for l in out.splitlines():
    p = l.split()
    if len(p) == 2 and p[0].lstrip("-").isdigit(): res[int(p[0])] = p[1]
bl = res[-1]
print("baseline:", bl)

changed = {k: [j for j in range(len(pairs)) if res[k][2*j:2*j+2] != bl[2*j:2*j+2]]
           for k in range(121)}
print("\nposition k (row=k//11, col=k%11) -> slices that differ from baseline")
for k in range(121):
    print(f"k={k:3d} r={k//11:2d} c={k%11:2d} -> {changed[k]}")

print("\nper-slice: which positions affect it")
for j in range(len(pairs)):
    ks = {k for k in range(121) if j in changed[k]}
    tag = "?"
    for r in range(11):
        if ks == {k for k in range(121) if k // 11 == r}: tag = f"ROW {r}"
    for c in range(11):
        if ks == {k for k in range(121) if k % 11 == c}: tag = f"COL {c}"
    print(f"slice {j:2d} (flops {pairs[j]}): {len(ks):3d} positions  {tag}",
          "" if tag != "?" else sorted(ks)[:20])
