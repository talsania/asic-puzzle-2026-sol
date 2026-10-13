import json, re, collections
import networkx as nx

D = json.load(open("puzzle_netlist.json")); cells, ports = D["cells"], D["ports"]
OUT = {"X", "Y", "Q", "HI", "LO"}
base = lambda c: re.sub(r"_\d+$", "", c)
FL = {"dfrtp", "dfstp", "dfxtp"}
pname = {v: k for k, v in ports.items()}
byid = {c["id"]: c for c in cells}
drv = {n: c for c in cells for k, n in c["pins"].items() if k in OUT}
flops = [c for c in cells if base(c["cell"]) in FL]

def cone(net):
    fl, cb, pt, seen, st = set(), set(), set(), set(), [net]
    while st:
        n = st.pop()
        if n in seen: continue
        seen.add(n)
        if n in pname: pt.add(pname[n])
        c = drv.get(n)
        if c is None: continue
        b = base(c["cell"])
        if b in FL: fl.add(c["id"]); continue
        if b == "conb": continue
        cb.add(c["id"])
        st.extend(m for k, m in c["pins"].items() if k not in OUT)
    return fl, cb, pt

info = {f["id"]: cone(f["pins"]["D"]) for f in flops}
G = nx.DiGraph(); G.add_nodes_from(info)
for f, (src, cb, pt) in info.items():
    for s in src: G.add_edge(s, f)

# ---- shift chains: D = mux(self, prev, enable) ----
nxt, heads = {}, []
for f, (src, cb, pt) in info.items():
    other = src - {f}
    if f in src and len(cb) <= 2:
        if len(other) == 1: nxt[next(iter(other))] = nxt.get(next(iter(other)), []) + [f]
        elif not other and "I" in pt: heads.append(f)
print("chain heads (D = mux(self, I)):", heads)
chained = set()
for h in heads:
    chain, cur = [h], h
    while len(nxt.get(cur, [])) == 1:
        cur = nxt[cur][0]; chain.append(cur)
    chained |= set(chain)
    print(f"  chain from {h}: length {len(chain)}, ids {chain}")
    if len(nxt.get(cur, [])) > 1: print("   ...fans out at", cur, "to", nxt[cur])

# ---- the rest: SCC summary ----
rest = [i for i in info if i not in chained]
H = G.subgraph(rest)
C = nx.condensation(H)
print(f"\nnon-chain flops: {len(rest)}, SCCs: {C.number_of_nodes()}")
for n in nx.topological_sort(C):
    m = sorted(C.nodes[n]["members"])
    xs = [byid[i]["x"] // 1000 for i in m]; ys = [byid[i]["y"] // 1000 for i in m]
    tp = collections.Counter(base(byid[i]["cell"]) for i in m)
    pts = set().union(*[info[i][2] for i in m])
    print(f"  SCC{n}: size={len(m)} in={C.in_degree(n)} out={C.out_degree(n)} "
          f"x={min(xs)}-{max(xs)} y={min(ys)}-{max(ys)} {dict(tp)} ports={sorted(pts)}")
    if len(m) <= 6: print("     ids:", m)

# ---- the success flop ----
s = drv[ports["success"]]
src, cb, pt = info[s["id"]]
print(f"\nsuccess flop id={s['id']} {s['cell']} at ({s['x']//1000},{s['y']//1000}) um")
print("  D cone: flops", sorted(src), " comb cells", len(cb), " ports", pt)
print("  cell mix:", dict(collections.Counter(base(byid[i]['cell']) for i in cb)))
print("  in chain:", s["id"] in chained)
# who reaches it
anc = nx.ancestors(G, s["id"]) | {s["id"]}
print("  flops that can reach success:", len(anc), "| in chains:", len(anc & chained),
      "| others:", len(anc - chained))
print("  O-only flops:", sorted(set(info) - anc))
