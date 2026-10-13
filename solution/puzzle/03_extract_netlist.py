import klayout.db as db, collections, re, json

ly = db.Layout(); ly.read("puzzle.gds")
top = ly.top_cells()[0]

COND = ["li1", "met1", "met2", "met3", "met4", "met5"]
VIAS = [("mcon", "li1", "met1"), ("via1", "met1", "met2"), ("via2", "met2", "met3"),
        ("via3", "met3", "met4"), ("via4", "met4", "met5")]
LAY = {"li1": (67, 20), "mcon": (67, 44), "met1": (68, 20), "via1": (68, 44),
       "met2": (69, 20), "via2": (69, 44), "met3": (70, 20), "via3": (70, 44),
       "met4": (71, 20), "via4": (71, 44), "met5": (72, 20)}
LABEL = {(67, 5): "li1", (68, 5): "met1", (69, 5): "met2",
         (70, 5): "met3", (71, 5): "met4", (72, 5): "met5"}
POWER = {"VPWR", "VGND", "VPB", "VNB"}
OUTPINS = {"X", "Y", "Q", "HI", "LO"}

# ---------- spatial index ----------
G = 4000
class Idx:
    def __init__(s, polys):
        s.polys = polys; s.g = collections.defaultdict(list)
        for i, p in enumerate(polys):
            b = p.bbox()
            for gx in range(b.left // G, b.right // G + 1):
                for gy in range(b.bottom // G, b.top // G + 1):
                    s.g[(gx, gy)].append(i)
    def at(s, pt):
        for i in s.g.get((pt.x // G, pt.y // G), ()):
            p = s.polys[i]
            if p.bbox().contains(pt) and p.inside(pt):
                return i
        return None

reg, idx = {}, {}
for n, (a, b) in LAY.items():
    li = ly.find_layer(a, b)
    reg[n] = db.Region(top.begin_shapes_rec(li)).merged() if li is not None else db.Region()
for c in COND:
    idx[c] = Idx(list(reg[c].each()))

parent = {}
def find(x):
    parent.setdefault(x, x)
    while parent[x] != x:
        parent[x] = parent[parent[x]]; x = parent[x]
    return x
def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb: parent[ra] = rb

bad_vias = 0
for via, lo, hi in VIAS:
    for v in reg[via].each():
        c = v.bbox().center()
        a, b = idx[lo].at(c), idx[hi].at(c)
        if a is None or b is None:
            bad_vias += 1; continue
        union((lo, a), (hi, b))
print("vias that missed a conductor:", bad_vias)

# ---------- collect leaf cells and their pin labels ----------
def is_leaf(n):
    if n.startswith("sky130_fd_sc_hd__"):
        return not any(k in n for k in ("decap", "tapvpwr", "diode"))
    return n.startswith("INTERNAL")

cells, unresolved = [], 0
for inst in top.each_inst():
    cn = inst.cell.name
    if not is_leaf(cn): continue
    tr = inst.cplx_trans
    c = dict(id=len(cells), cell=cn.replace("sky130_fd_sc_hd__", ""),
             x=tr.disp.x, y=tr.disp.y, pins={})
    cells.append(c)
    for (l, d), cond in LABEL.items():
        li = ly.find_layer(l, d)
        if li is None: continue
        it = db.RecursiveShapeIterator(ly, inst.cell, li)
        while not it.at_end():
            sh = it.shape()
            if sh.is_text():
                t = sh.text
                p = tr * (it.trans() * db.Point(t.x, t.y))
                if t.string not in POWER:
                    i = idx[cond].at(p)
                    if i is None:
                        unresolved += 1; print("UNRESOLVED", c["id"], cn, t.string)
                    else:
                        c["pins"][t.string] = find((cond, i))
            it.next()
print("cells:", len(cells), " unresolved pins:", unresolved)

# ---------- top-level ports ----------
ports = {}
for li in ly.layer_indexes():
    info = ly.get_info(li)
    cond = LABEL.get((info.layer, info.datatype))
    if not cond: continue
    for sh in top.shapes(li).each():
        if sh.is_text() and sh.text.string not in POWER:
            i = idx[cond].at(db.Point(sh.text.x, sh.text.y))
            ports[sh.text.string] = find((cond, i)) if i is not None else None
print("ports:", ports)

# ---------- net naming ----------
names = {}
def nn(root):
    return names.setdefault(root, f"n{len(names)}")
for c in cells:
    c["pins"] = {k: nn(v) for k, v in c["pins"].items()}
json.dump(dict(cells=cells, ports={k: nn(v) for k, v in ports.items() if v is not None}),
          open("puzzle_netlist.json", "w"), indent=1)

# ---------- gate functions (N() = invert) ----------
F = {
 "inv":"N(A)","buf":"A","clkbuf":"A","clkdlybuf4s50":"A",
 "nand2":"N(A&B)","nand3":"N(A&B&C)","nand4":"N(A&B&C&D)",
 "nand2b":"N(N(A_N)&B)","nand3b":"N(N(A_N)&B&C)",
 "nor2":"N(A|B)","nor3":"N(A|B|C)","nor4":"N(A|B|C|D)",
 "nor3b":"N(A|B|N(C_N))","nor4b":"N(A|B|C|N(D_N))",
 "and2":"A&B","and3":"A&B&C","and4":"A&B&C&D",
 "and2b":"N(A_N)&B","and3b":"N(A_N)&B&C","and4b":"N(A_N)&B&C&D",
 "and4bb":"N(A_N)&N(B_N)&C&D",
 "or2":"A|B","or3":"A|B|C","or4":"A|B|C|D",
 "or3b":"A|B|N(C_N)","or4b":"A|B|C|N(D_N)","or4bb":"A|B|N(C_N)|N(D_N)",
 "xor2":"A^B","xnor2":"N(A^B)",
 "a21o":"(A1&A2)|B1","a21oi":"N((A1&A2)|B1)",
 "a21bo":"(A1&A2)|N(B1_N)","a21boi":"N((A1&A2)|N(B1_N))",
 "a22o":"(A1&A2)|(B1&B2)","a22oi":"N((A1&A2)|(B1&B2))",
 "a31o":"(A1&A2&A3)|B1","a31oi":"N((A1&A2&A3)|B1)",
 "a32o":"(A1&A2&A3)|(B1&B2)","a41oi":"N((A1&A2&A3&A4)|B1)",
 "a211o":"(A1&A2)|B1|C1","a211oi":"N((A1&A2)|B1|C1)",
 "a221o":"(A1&A2)|(B1&B2)|C1","a221oi":"N((A1&A2)|(B1&B2)|C1)",
 "a311o":"(A1&A2&A3)|B1|C1","a2111oi":"N((A1&A2)|B1|C1|D1)",
 "o21a":"(A1|A2)&B1","o21ai":"N((A1|A2)&B1)",
 "o21ba":"(A1|A2)&N(B1_N)","o21bai":"N((A1|A2)&N(B1_N))",
 "o211a":"(A1|A2)&B1&C1","o211ai":"N((A1|A2)&B1&C1)",
 "o22a":"(A1|A2)&(B1|B2)","o22ai":"N((A1|A2)&(B1|B2))",
 "o221a":"(A1|A2)&(B1|B2)&C1",
 "o31a":"(A1|A2|A3)&B1","o31ai":"N((A1|A2|A3)&B1)",
 "o311a":"(A1|A2|A3)&B1&C1",
 "o32a":"(A1|A2|A3)&(B1|B2)","o32ai":"N((A1|A2|A3)&(B1|B2))",
 "o2bb2a":"(N(A1_N)|N(A2_N))&(B1|B2)",
 "mux2":"(S&A1)|(N(S)&A0)",
}
def base(cn): return re.sub(r"_\d+$", "", cn)

out, regs, unknown = [], set(), collections.Counter()
drivers = collections.Counter()
for c in cells:
    b, p = base(c["cell"]), c["pins"]
    for k, n in p.items():
        if k in OUTPINS: drivers[n] += 1
    try:
        if b == "dfrtp":
            regs.add(p["Q"])
            out.append(f"always @(posedge {p['CLK']} or negedge {p['RESET_B']}) "
                       f"if(!{p['RESET_B']}) {p['Q']}<=0; else {p['Q']}<={p['D']};")
        elif b == "dfstp":
            regs.add(p["Q"])
            out.append(f"always @(posedge {p['CLK']} or negedge {p['SET_B']}) "
                       f"if(!{p['SET_B']}) {p['Q']}<=1; else {p['Q']}<={p['D']};")
        elif b == "dfxtp":
            regs.add(p["Q"])
            out.append(f"always @(posedge {p['CLK']}) {p['Q']}<={p['D']};")
        elif b == "conb":
            if "HI" in p: out.append(f"assign {p['HI']} = 1'b1;")
            if "LO" in p: out.append(f"assign {p['LO']} = 1'b0;")
        elif b in F:
            o = next(k for k in ("X", "Y") if k in p)
            e = re.sub(r"\b[A-Z][A-Z0-9_]*\b",
                       lambda m: "~" if m.group() == "N" else p[m.group()], F[b])
            out.append(f"assign {p[o]} = {e};")
        else:
            unknown[c["cell"]] += 1
    except (KeyError, StopIteration) as ex:
        print("PIN PROBLEM", c["id"], c["cell"], "missing", ex, "has", sorted(p))

print("unknown cell types (not emitted):", dict(unknown))

pn = {k: nn(v) for k, v in ports.items() if v is not None}
for k in pn: drivers[pn[k]] += 1 if k in ("I", "enable", "clk", "rst_n") else 0
allnets = set(names.values())
print("nets:", len(allnets), " undriven:", sum(1 for n in allnets if drivers[n] == 0),
      " multi-driven:", sum(1 for n in allnets if drivers[n] > 1))

with open("puzzle_netlist.v", "w") as f:
    f.write("module puzzle(input clk, input rst_n, input I, input enable,"
            " output [7:0] O, output success);\n")
    for n in sorted(allnets, key=lambda s: int(s[1:])):
        f.write(f"  {'reg' if n in regs else 'wire'} {n};\n")
    for k in ("clk", "rst_n", "I", "enable"):
        if k in pn: f.write(f"  assign {pn[k]} = {k};\n")
    for i in range(8):
        if f"O[{i}]" in pn: f.write(f"  assign O[{i}] = {pn[f'O[{i}]']};\n")
    if "success" in pn: f.write(f"  assign success = {pn['success']};\n")
    for l in out: f.write("  " + l + "\n")
    f.write("endmodule\n")
print("wrote puzzle_netlist.v")
