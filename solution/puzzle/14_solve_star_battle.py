import subprocess, collections

N = 11
# ---------- regions, straight from the chip ----------
out = subprocess.run(["vvp", "exp.vvp"], capture_output=True, text=True).stdout
res = {}
for l in out.splitlines():
    p = l.split()
    if len(p) == 2 and p[0].lstrip("-").isdigit(): res[int(p[0])] = p[1]
bl = res[-1]; region = []
for k in range(N * N):
    ch = [j for j in range(22) if res[k][2*j:2*j+2] != bl[2*j:2*j+2]]
    region.append([j for j in ch if j >= 11][0] - 11)
G = lambda r, c: region[r * N + c]
rem = [[sum(1 for rr in range(r, N) for cc in range(N) if G(rr, cc) == g) for g in range(11)] for r in range(N + 1)]

# ---------- Star Battle: 2 per row/col/region, no touching ----------
sols = []
def rec(r, prev, cc, rc, placed):
    if r == N:
        if all(x == 2 for x in cc) and all(x == 2 for x in rc): sols.append(tuple(placed))
        return
    left = N - r
    for c in range(N):
        if 2 - cc[c] > left: return
    for g in range(11):
        if 2 - rc[g] > rem[r][g]: return
    for c1 in range(N):
        if cc[c1] >= 2: continue
        for c2 in range(c1 + 2, N):
            if cc[c2] >= 2: continue
            if any(abs(c - p) < 2 for c in (c1, c2) for p in prev): continue
            ncc = cc[:]; ncc[c1] += 1; ncc[c2] += 1
            nrc = rc[:]; nrc[G(r, c1)] += 1; nrc[G(r, c2)] += 1
            if max(nrc) > 2: continue
            rec(r + 1, (c1, c2), ncc, nrc, placed + [(c1, c2)])
rec(0, (), [0] * N, [0] * 11, [])
print("Star Battle solutions:", len(sols))
if not sols: raise SystemExit("none - the rule needs another look")

def bits(s):
    b = ["0"] * 121
    for r, (c1, c2) in enumerate(s): b[r*N + c1] = b[r*N + c2] = "1"
    return "".join(b)
def show(s):
    for r in range(N):
        print("  " + " ".join("*" if c in s[r] else "." for c in range(N)))

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
    rst_n = 0; enable = 0; I = 0; repeat (3) @(negedge clk);
    rst_n = 1; @(negedge clk); enable = 1;
    for (t = 0; t < 121; t = t + 1) begin I = cand[i][120 - t]; @(negedge clk); end
    enable = 0; I = 0;
    for (c = 0; c < POST; c = c + 1) begin @(negedge clk); $display("R %0d %0d %b %h", i, c, success, O); end
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
        if len(p) == 5 and p[0] == "R": rows[int(p[1])].append((int(p[2]), p[3], int(p[4], 16)))
    return rows

use = sols[:200]
rows = simulate([bits(s) for s in use], post=12)
wins = [i for i, r in rows.items() if any(x[1] == "1" for x in r)]
print("candidates that raise success:", len(wins), "of", len(use))
if not wins:
    print("none - paste this and I'll look at flop 412 / the prev0 term")
    raise SystemExit
w = use[wins[0]]
print("winner:"); show(w)

# ---------- decode O for the winner ----------
r = simulate([bits(w)], post=4000)[0]
first = next(c for c, s, o in r if s == "1")
print("success first high", first, "cycles after the stream; stays high:",
      all(s == "1" for c, s, o in r if c >= first))
seq = [o for c, s, o in r if s == "1"]
print("first 64 O values:", seq[:64])
asc = lambda v: "".join(chr(x) if 32 <= x < 127 else "." for x in v)
print("ASCII:", asc(seq[:200]))
for p in range(1, len(seq) // 2):
    if all(seq[i] == seq[i + p] for i in range(len(seq) - p)):
        print(f"\nO repeats with period {p}:"); print(" ", asc(seq[:p])); print("  ", seq[:p]); break
else:
    print("no period found in", len(seq), "cycles")
