import json, random

D = json.load(open("warmup_netlist.json"))
cells, ports = D["cells"], D["ports"]

# ---- cell library (outputs: X, Y, Q) ----
FUNC = {
    "nand2":  lambda p: 1 - (p["A"] & p["B"]),
    "nor2":   lambda p: 1 - (p["A"] | p["B"]),
    "and2":   lambda p: p["A"] & p["B"],
    "or2":    lambda p: p["A"] | p["B"],
    "xor2":   lambda p: p["A"] ^ p["B"],
    "xnor2":  lambda p: 1 - (p["A"] ^ p["B"]),
    "and3":   lambda p: p["A"] & p["B"] & p["C"],
    "clkbuf_16": lambda p: p["A"],
    "and4bb": lambda p: (1 - p["A_N"]) & (1 - p["B_N"]) & p["C"] & p["D"],
    "a21o":   lambda p: (p["A1"] & p["A2"]) | p["B1"],
    "a21bo":  lambda p: (p["A1"] & p["A2"]) | (1 - p["B1_N"]),
    "a21boi": lambda p: 1 - ((p["A1"] & p["A2"]) | (1 - p["B1_N"])),
    "o21bai": lambda p: 1 - ((p["A1"] | p["A2"]) & (1 - p["B1_N"])),
    "a31o":   lambda p: (p["A1"] & p["A2"] & p["A3"]) | p["B1"],
    "mux2_1": lambda p: p["A1"] if p["S"] else p["A0"],
}
OUT = ("X", "Y", "Q")
POWER = ("VPWR", "VGND", "VPB", "VNB")

def key(c):  # strip drive-strength suffix when not in table
    return c if c in FUNC else c.rsplit("_", 1)[0]

comb, flops = [], []
for c in cells:
    ins = {k: v for k, v in c["pins"].items() if k not in POWER}
    if c["cell"].startswith("dfrtp"):
        flops.append((ins["D"], ins["RESET_B"], ins["CLK"], ins["Q"]))
        continue
    outpin = next(k for k in ins if k in OUT)
    inpins = {k: v for k, v in ins.items() if k not in OUT}
    f = FUNC[c["cell"]] if c["cell"] in FUNC else FUNC[key(c["cell"])]
    comb.append((f, inpins, ins[outpin]))

class Chip:
    def __init__(self):
        self.v = {}
        self.set("rst_n", 0); self.set("clk", 0)
        self.set("A", 0); self.set("B", 0); self.set("en", 0)
        self.settle()
    def set(self, name, val): self.v[ports[name]] = val
    def get(self, name): return self.v.get(ports[name], 0)
    def settle(self):
        rst = self.get("rst_n")
        for _ in range(200):
            changed = False
            for d, rb, clk, q in flops:
                if not self.v.get(rb, 1) and self.v.get(q, 0) != 0:
                    self.v[q] = 0; changed = True
            for f, inp, out in comb:
                new = f({k: self.v.get(n, 0) for k, n in inp.items()})
                if self.v.get(out) != new:
                    self.v[out] = new; changed = True
            if not changed: return
        raise RuntimeError("did not settle (combinational loop?)")
    def reset(self):
        self.set("rst_n", 0); self.settle()
        self.set("rst_n", 1); self.settle()
    def clock(self, A, B, en):
        self.set("A", A); self.set("B", B); self.set("en", en); self.set("clk", 0)
        self.settle()
        nxt = [(q, self.v.get(d, 0)) for d, rb, clk, q in flops if self.v.get(rb, 1)]
        self.set("clk", 1)
        for q, val in nxt: self.v[q] = val
        self.settle()
        self.set("clk", 0); self.settle()
        return self.get("S")

# ---- 1. verify against the Verilog behaviour ----
random.seed(1)
ok = True
for trial in range(300):
    chip = Chip(); chip.reset()
    a = b = 0
    for t in range(random.randint(1, 40)):
        A, B, en = random.getrandbits(1), random.getrandbits(1), random.getrandbits(1)
        S = chip.clock(A, B, en)
        if en:
            a = ((a << 1) | A) & 0xFF
            b = ((b << 1) | B) & 0xFF
        if S != int(a + b == 496):
            ok = False; print("MISMATCH", trial, t, a, b, S)
print("netlist matches source on random tests:", ok)

# ---- 2. drive S high: A=248, B=248, MSB first ----
def run(a, b):
    chip = Chip(); chip.reset()
    for i in range(7, -1, -1):
        S = chip.clock((a >> i) & 1, (b >> i) & 1, 1)
    return S

print("A=248, B=248 -> S =", run(248, 248))
print("A=255, B=241 -> S =", run(255, 241))
print("A=1,   B=2   -> S =", run(1, 2))
sols = [(a, b) for a in range(256) for b in range(256) if run(a, b)]
print(len(sols), "input pairs make S=1; e.g.", sols[:5])
