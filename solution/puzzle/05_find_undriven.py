import json, collections
D = json.load(open("puzzle_netlist.json"))
OUT = {"X","Y","Q","HI","LO"}; IGN = {"VPWR","VGND","VPB","VNB"}
drv, loads = collections.Counter(), collections.defaultdict(list)
for c in D["cells"]:
    for k, n in c["pins"].items():
        (drv.__setitem__(n, drv[n]+1) if k in OUT else loads[n].append((c["id"], c["cell"], k, c["x"], c["y"])))
ext = set(D["ports"].values())
for n in set(loads) | set(drv):
    if drv[n] == 0 and n not in ext:
        print("UNDRIVEN", n, loads[n])
# nets that drive nothing (apart from output ports)
print("dangling outputs:", sum(1 for n in drv if n not in loads and n not in ext))
