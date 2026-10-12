import json, collections
D = json.load(open("puzzle_netlist.json"))
OUT = {"X","Y","Q","HI","LO"}
loads = collections.Counter(); drv = {}
for c in D["cells"]:
    for k, n in c["pins"].items():
        if k in OUT: drv[n] = (c["id"], c["cell"], k, c["x"], c["y"])
        else: loads[n] += 1
ext = set(D["ports"].values())
print("dangling drivers near the undriven net (x 160000-200000, y 70000-120000):")
for n, d in drv.items():
    if loads[n] == 0 and n not in ext:
        flag = "  <-- near" if 160000 < d[3] < 200000 and 70000 < d[4] < 120000 else ""
        print(n, d, flag)
