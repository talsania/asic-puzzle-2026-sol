import klayout.db as db, json, collections

ly = db.Layout()
ly.read("warmup/04_final.gds")
top = ly.top_cell()

COND = ["li1", "met1", "met2", "met3", "met4", "met5"]
VIAS = [("mcon", "li1", "met1"), ("via1", "met1", "met2"), ("via2", "met2", "met3"),
        ("via3", "met3", "met4"), ("via4", "met4", "met5")]
LAY = {"li1": (67, 20), "mcon": (67, 44), "met1": (68, 20), "via1": (68, 44),
       "met2": (69, 20), "via2": (69, 44), "met3": (70, 20), "via3": (70, 44),
       "met4": (71, 20), "via4": (71, 44), "met5": (72, 20)}
LABEL = {(67, 5): "li1", (68, 5): "met1", (69, 5): "met2",
         (70, 5): "met3", (71, 5): "met4", (72, 5): "met5"}

# ---------- 1. merged regions (flattened view) ----------
reg = {}
for n, (a, b) in LAY.items():
    li = ly.find_layer(a, b)
    reg[n] = db.Region(top.begin_shapes_rec(li)).merged() if li is not None else db.Region()

# ---------- 2. union-find over (layer, polygon index) ----------
parent = {}
def find(x):
    parent.setdefault(x, x)
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x
def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[ra] = rb

polys, index = {}, {}
for c in COND:
    polys[c] = list(reg[c].each())
    index[c] = {p.to_s(): i for i, p in enumerate(polys[c])}
    for i in range(len(polys[c])):
        find((c, i))

def hits(layer, region):
    return [index[layer][p.to_s()] for p in reg[layer].interacting(region).each()]

for via, lo, hi in VIAS:
    for v in reg[via].each():
        vr = db.Region(v)
        lows, highs = hits(lo, vr), hits(hi, vr)
        group = [(lo, i) for i in lows] + [(hi, i) for i in highs]
        for g in group[1:]:
            union(group[0], g)

def net_at(layer, p):
    r = db.Region(db.Box(p.x - 1, p.y - 1, p.x + 1, p.y + 1))
    h = hits(layer, r)
    return find((layer, h[0])) if h else None

# ---------- 3. pin labels inside each logic cell ----------
insts, cells = [], []
for inst in top.each_inst():
    cn = inst.cell.name
    if not cn.startswith("sky130_fd_sc_hd__") or "decap" in cn or "tapvpwr" in cn:
        continue
    tr = inst.cplx_trans
    c = dict(id=len(cells), cell=cn.replace("sky130_fd_sc_hd__", ""),
             x=tr.disp.x, y=tr.disp.y, pins={})
    cells.append(c)
    for lab, cond in LABEL.items():
        li = ly.find_layer(*lab)
        if li is None:
            continue
        for sh in inst.cell.shapes(li).each():
            if not sh.is_text():
                continue
            t = sh.text
            p = tr * db.Point(t.x, t.y)
            n = net_at(cond, p)
            if n is None:
                print("UNRESOLVED", c["id"], cn, t.string, cond)
                continue
            old = c["pins"].get(t.string)
            if old is not None and old != n:
                print("CONFLICT: same pin on two nets", c["id"], cn, t.string)
            c["pins"][t.string] = n

# ---------- 4. every text in the top cell (the I/O ports) ----------
print("\nTop-level texts:")
ports = {}
for li in ly.layer_indexes():
    info = ly.get_info(li)
    for sh in top.shapes(li).each():
        if sh.is_text():
            t = sh.text
            cond = LABEL.get((info.layer, info.datatype))
            n = net_at(cond, db.Point(t.x, t.y)) if cond else None
            print(f"  {info.layer}/{info.datatype}  {t.string!r}  ({t.x},{t.y})  net={n}")
            if n is not None:
                ports[t.string] = n

# ---------- 5. renumber nets and save ----------
ids = {}
def nid(n):
    return ids.setdefault(n, len(ids))
for c in cells:
    c["pins"] = {k: nid(v) for k, v in c["pins"].items()}
ports = {k: nid(v) for k, v in ports.items()}
json.dump(dict(cells=cells, ports=ports), open("warmup_netlist.json", "w"), indent=1)

print("\ncells:", len(cells), " nets:", len(ids))
missing = [(c["id"], c["cell"]) for c in cells if len(c["pins"]) < 3]
print("cells with <3 pins resolved:", missing)
