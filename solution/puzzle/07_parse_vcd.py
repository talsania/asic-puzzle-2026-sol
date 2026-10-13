import re
ids, val, t = {}, {}, 0
ev = []
for line in open("example_inputs.vcd"):
    line = line.strip()
    m = re.match(r"\$var\s+\S+\s+\d+\s+(\S+)\s+(\S+)", line)
    if m: ids[m.group(1)] = m.group(2); continue
    if line.startswith("#"): t = int(line[1:]); continue
    m = re.match(r"^([01xz])(\S+)$", line)
    if m and m.group(2) in ids:
        name = ids[m.group(2)]
        if name != "clk": ev.append((t, name, m.group(1)))
print("signals:", list(ids.values()))
print("last time:", t, " -> cycles of 10000:", t // 10000)
for t, n, v in ev[:80]: print(f"t={t:>9}  cycle={t/10000:>8.1f}  {n} = {v}")
print("... total non-clk events:", len(ev))
