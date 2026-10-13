import subprocess, collections

N = 11
# ---------- 1. regions, straight from the chip ----------
out = subprocess.run(["vvp", "exp.vvp"], capture_output=True, text=True).stdout
res = {}
for l in out.splitlines():
    p = l.split()
    if len(p) == 2 and p[0].lstrip("-").isdigit(): res[int(p[0])] = p[1]
bl = res[-1]
region = []
for k in range(N * N):
    ch = [j for j in range(22) if res[k][2*j:2*j+2] != bl[2*j:2*j+2]]
    cols = [j for j in ch if j < 11]; regs = [j for j in ch if j >= 11]
    assert len(cols) == 1 and len(regs) == 1, (k, ch)
    region.append(regs[0] - 11)
print("regions as seen by the chip:")
for r in range(N):
    print("  " + " ".join(chr(65 + region[r*N + c]) for c in range(N)))
print("region sizes:", dict(collections.Counter(chr(65 + g) for g in region)))

# ---------- 2. enumerate placements ----------
def solve(adj):
    sols = []
    def rec(r, cols, regs, placed):
        if r == N: sols.append(tuple(placed)); return
        for c in range(N):
            if c in cols: continue
            g = region[r * N + c]
            if g in regs: continue
            if adj and placed and abs(placed[-1] - c) <= 1: continue
            rec(r + 1, cols | {c}, regs | {g}, placed + [c])
    rec(0, frozenset(), frozenset(), [])
    return sols

def bits(sol):
    b = ["0"] * (N * N)
    for r, c in enumerate(sol): b[r * N + c] = "1"
    return "".join(b)

def show(sol):
    for r in range(N):
        print("  " + " ".join("Q" if sol[r] == c else "." for c in range(N)))

# ---------- 3. simulate candidates on the extracted netlist ----------
def simulate(cands, post):
    open("cands.txt", "w").write("\n".join(cands) + "\n")
    tb = """`timescale 1ns/1ps
module tb;
reg clk=0, rst_n=0, I=0, enable=0;
wire [7:0] O; wire success;
puzzle dut(.clk(clk),.rst_n(rst_n),.I(I),.enable(enable),.O(O),.success(success));
always #5 clk = ~clk;
reg [120:0] cand [0:NC-1];
integer i, t, c;
initial begin
  $readmemb("cands.txt", cand);
  for (i = 0; i < NC; i = i + 1) begin
    rst_n = 0; enable = 0; I = 0;
    repeat (3) @(negedge clk);
    rst_n = 1; @(negedge clk);
    enable = 1;
    for (t = 0; t < 121; t = t + 1) begin I = cand[i][120 - t]; @(negedge clk); end
    enable = 0; I = 0;
    for (c = 0; c < POST; c = c + 1) begin
      @(negedge clk); $display("R %0d %0d %b %h", i, c, success, O);
    end
  end
  $finish;
end
endmodule
""".replace("NC", str(len(cands))).replace("POST", str(post))
    open("tb_solve.v", "w").write(tb)
    subprocess.run(["iverilog", "-o", "solve.vvp", "tb_solve.v", "puzzle_netlist.v"], check=True)
    o = subprocess.run(["vvp", "solve.vvp"], capture_output=True, text=True).stdout
    rows = collections.defaultdict(list)
    for l in o.splitlines():
        p = l.split()
        if len(p) == 5 and p[0] == "R": rows[int(p[1])].append((int(p[2]), p[3], p[4]))
    return rows

winner = None
for adj in (True, False):
    sols = solve(adj)
    print(f"\nplacements with adjacency rule={adj}: {len(sols)}")
    if not sols: continue
    if len(sols) > 3000:
        print("  too many; truncating to 3000"); sols = sols[:3000]
    rows = simulate([bits(s) for s in sols], post=40)
    wins = [i for i, r in rows.items() if any(x[1] == "1" for x in r)]
    print(f"  candidates that make success go high: {len(wins)}")
    if wins:
        winner = sols[wins[0]]
        print("  winner:", winner)
        show(winner)
        break

# ---------- 4. read the output of the winner ----------
if winner:
    rows = simulate([bits(winner)], post=1500)[0]
    seq = [(c, int(o, 16)) for c, s, o in rows if s == "1"]
    print("\ncycles with success=1:", len(seq), " first success at cycle:", seq[0][0] if seq else None)
    print("O values at success (first 120):", [v for _, v in seq[:120]])
    asc = "".join(chr(v) if 32 <= v < 127 else "." for _, v in seq)
    print("as ASCII:", asc)
    last = None; trans = []
    for c, v in seq:
        if v != last: trans.append(v); last = v
    print("on change:", "".join(chr(v) if 32 <= v < 127 else "." for v in trans))
    print("raw change list:", trans[:80])
