import json, re, collections
D = json.load(open("puzzle_netlist.json"))
cells = D["cells"]; ports = D["ports"]
OUT = {"X", "Y", "Q", "HI", "LO"}
base = lambda c: re.sub(r"_\d+$", "", c)
FLOPS = {"dfrtp", "dfstp", "dfxtp"}
CTRL = {"CLK", "RESET_B", "SET_B"}

drv = {}                       # net -> cell
for c in cells:
    for k, n in c["pins"].items():
        if k in OUT: drv[n] = c
ins = lambda c: {k: n for k, n in c["pins"].items() if k not in OUT and k not in CTRL}
flops = [c for c in cells if base(c["cell"]) in FLOPS]
print("flops:", len(flops), collections.Counter(base(c["cell"]) for c in flops))
print("distinct clock nets:", len({c["pins"]["CLK"] for c in flops}),
      " reset nets:", len({c["pins"].get("RESET_B", c["pins"].get("SET_B")) for c in flops}))

def cone(net, seen=None):
    """combinational fan-in of a net: returns (set of flop ids reached, set of comb cell ids, set of ports reached)."""
    fl, cb, pt = set(), set(), set()
    stack, seen = [net], set()
    pnames = {v: k for k, v in ports.items()}
    while stack:
        n = stack.pop()
        if n in seen: continue
        seen.add(n)
        if n in pnames: pt.add(pnames[n])
        c = drv.get(n)
        if c is None: continue
        if base(c["cell"]) in FLOPS: fl.add(c["id"]); continue
        if base(c["cell"]) == "conb": continue
        cb.add(c["id"]); stack.extend(ins(c).values())
    return fl, cb, pt

# one-step flop graph: for each flop, which flops/ports feed its D
fan = {}
for f in flops:
    fl, cb, pt = cone(f["pins"]["D"])
    fan[f["id"]] = (fl, cb, pt)
print("\nflops whose D is fed by exactly one flop (shift-chain candidates):",
      sum(1 for v in fan.values() if len(v[0]) == 1))
print("flops whose D is fed directly by port I:",
      [i for i, v in fan.items() if v[2] == {"I"} and len(v[0]) == 0])

# cones of success and each O bit
succ_fl, succ_cb, succ_pt = cone(ports["success"])
print("\nsuccess: %d flops, %d comb cells, ports=%s" % (len(succ_fl), len(succ_cb), succ_pt))
allO = set()
for i in range(8):
    fl, cb, pt = cone(ports[f"O[{i}]"])
    allO |= fl
    print(f"O[{i}]: {len(fl)} flops, {len(cb)} comb cells, ports={pt}")
print("\nflops in success cone only :", len(succ_fl - allO))
print("flops in O cones only      :", len(allO - succ_fl))
print("flops in both              :", len(succ_fl & allO))
print("flops in neither           :", len({f['id'] for f in flops} - succ_fl - allO))

# transitive sequential closure: which flops can *ever* influence success
def reach(seeds):
    got, todo = set(), list(seeds)
    while todo:
        f = todo.pop()
        if f in got: continue
        got.add(f); todo.extend(fan[f][0])
    return got
S = reach(succ_fl); O = reach(allO)
print("\nflops that can ever affect success:", len(S))
print("flops that can ever affect O      :", len(O))
print("flops only affecting O (output generator)  :", len(O - S))
print("flops affecting neither:", len({f['id'] for f in flops} - S - O))

# placement: bounding box of each group
def bbox(ids):
    xs = [cells[i]["x"] for i in ids]; ys = [cells[i]["y"] for i in ids]
    return (min(xs) // 1000, min(ys) // 1000, max(xs) // 1000, max(ys) // 1000) if ids else None
print("\nbbox (um) of success-side flops:", bbox(S))
print("bbox (um) of O-only flops      :", bbox(O - S))

json.dump({"success_flops": sorted(S), "o_only_flops": sorted(O - S)}, open("groups.json", "w"))
