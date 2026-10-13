import json, re, subprocess, collections
D = json.load(open("puzzle_netlist.json")); cells = D["cells"]; ports = D["ports"]
pairs = json.load(open("pairs.json"))
OUT = {"X","Y","Q","HI","LO"}; FL = {"dfrtp","dfstp","dfxtp"}
base = lambda c: re.sub(r"_\d+$", "", c)
byid = {c["id"]: c for c in cells}
drv = {n: c for c in cells for k, n in c["pins"].items() if k in OUT}
Qn = lambda i: byid[i]["pins"]["Q"]
N = 11

# ---- grid/regions straight from the chip (same as solve.py) ----
o = subprocess.run(["vvp", "exp.vvp"], capture_output=True, text=True).stdout
res = {}
for l in o.splitlines():
    p = l.split()
    if len(p) == 2 and p[0].lstrip("-").isdigit(): res[int(p[0])] = p[1]
bl = res[-1]; colOf, region = {}, [0]*121
for k in range(121):
    ch = [j for j in range(22) if res[k][2*j:2*j+2] != bl[2*j:2*j+2]]
    colOf[[j for j in ch if j < 11][0]] = k % 11
    region[k] = [j for j in ch if j >= 11][0] - 11

# ---- labels ----
label = {}
for j, p in enumerate(pairs):
    nm = f"C{colOf[j]}" if j < 11 else f"R{chr(65+j-11)}"
    for t, i in enumerate(p): label[Qn(i)] = f"{nm}.{'ab'[t]}"
for t, i in enumerate([348,355,345,347,464,468,460,461,343]): label[Qn(i)] = f"ct{t}"
for t, i in enumerate([446,444,442,440,453,452,454,447]): label[Qn(i)] = f"pop{t}"
for t, i in enumerate([382,381,383,387,386,396,360,385,363,389,371,391]): label[Qn(i)] = f"prev{t}"
for c in cells:
    if base(c["cell"]) in FL: label.setdefault(Qn(c["id"]), f"f{c['id']}")
    if base(c["cell"]) == "conb":
        for k, n in c["pins"].items():
            if k in ("HI", "LO"): label[n] = k
nm = lambda n: label.get(n, n)

# ---- 1. success.D cone ----
sf = drv[ports["success"]]; dnet = sf["pins"]["D"]
order, seen = [], set()
def visit(n):
    if n in seen: return
    seen.add(n); c = drv.get(n)
    if c is None or base(c["cell"]) in FL or base(c["cell"]) == "conb": return
    for k, m in c["pins"].items():
        if k not in OUT: visit(m)
    order.append(c)
visit(dnet)
outnet = lambda c: next(v for k, v in c["pins"].items() if k in OUT)

# ---- helpers: run candidates through the chip ----
def run(cands, expr, wait):
    open("cands.txt", "w").write("\n".join(cands) + "\n")
    tb = """`timescale 1ns/1ps
module tb;
reg clk=0, rst_n=0, I=0, enable=0;
wire [7:0] O; wire success;
puzzle dut(.clk(clk),.rst_n(rst_n),.I(I),.enable(enable),.O(O),.success(success));
always #5 clk = ~clk;
reg [120:0] cand [0:NC-1];
integer i, t;
initial begin
  $readmemb("cands.txt", cand);
  for (i = 0; i < NC; i = i + 1) begin
    rst_n = 0; enable = 0; I = 0; repeat (3) @(negedge clk);
    rst_n = 1; @(negedge clk); enable = 1;
    for (t = 0; t < 121; t = t + 1) begin I = cand[i][120 - t]; @(negedge clk); end
    enable = 0; I = 0; repeat (WAIT) @(negedge clk);
    $display("R %0d %b", i, {EXPR});
  end
  $finish;
end
endmodule
""".replace("NC", str(len(cands))).replace("WAIT", str(wait)).replace("EXPR", expr)
    open("tb_diag.v", "w").write(tb)
    subprocess.run(["iverilog", "-o", "diag.vvp", "tb_diag.v", "puzzle_netlist.v"], check=True)
    out = subprocess.run(["vvp", "diag.vvp"], capture_output=True, text=True).stdout
    return {int(l.split()[1]): l.split()[2] for l in out.splitlines() if l.startswith("R ")}

def mk(ones):
    b = ["0"] * 121
    for k in ones: b[k] = "1"
    return "".join(b)

# ---- 2. what does a slice's state mean? ----
lines, cands = [], []
for j in range(22):
    cl = [k for k in range(121) if (k % 11 == colOf[j])] if j < 11 else [k for k in range(121) if region[k] == j - 11]
    for n in range(6): cands.append(mk(cl[:n]))
allq = ", ".join("dut." + Qn(i) for p in pairs for i in p)
r = run(cands, allq, 0)
print("slice state after n ones inside that line/region (n = 0..5), as bits of its two flops")
for j in range(22):
    nmj = f"C{colOf[j]}" if j < 11 else f"R{chr(65+j-11)}"
    st = [r[j*6+n][2*j:2*j+2] for n in range(6)]
    print(f"  {nmj:>3}: ", " ".join(st))

# ---- 3. queen-valid candidates vs. the success tree ----
def solve():
    sols = []
    def rec(rw, cols, regs, placed):
        if rw == N: sols.append(tuple(placed)); return
        for c in range(N):
            if c in cols or region[rw*N+c] in regs: continue
            if placed and abs(placed[-1] - c) <= 1: continue
            rec(rw+1, cols|{c}, regs|{region[rw*N+c]}, placed+[c])
    rec(0, frozenset(), frozenset(), []); return sols
sols = solve(); pick = [sols[0], sols[len(sols)//2], sols[-1]]
ex = ", ".join("dut." + outnet(c) for c in order) + ", dut." + dnet
r = run([mk([rw*N+c for rw, c in enumerate(s)]) for s in pick], ex, 1)
print("\nsuccess.D tree: gate definitions and values for 3 queen-valid candidates (1 cycle after stream)")
for g, c in enumerate(order):
    args = ", ".join(f"{k}={nm(m)}" for k, m in c["pins"].items() if k not in OUT)
    vals = " ".join(r[i][g] for i in range(3))
    print(f"  {outnet(c):>5} = {base(c['cell'])}({args})   -> {vals}")
print(f"  success.D = {nm(dnet)}   -> " + " ".join(r[i][-1] for i in range(3)))
