import klayout.db as db

ly = db.Layout()
ly.read("warmup/04_final.gds")
print("dbu:", ly.dbu)
print("top cells:", [c.name for c in ly.top_cells()])
print("total cells:", ly.cells())

print("\nLayers:")
for li in ly.layer_indexes():
    info = ly.get_info(li)
    n = sum(c.shapes(li).size() for c in ly.each_cell())
    print(f"  {info.layer}/{info.datatype}  {info.name!r}  shapes={n}")

print("\nCell names (first 40):")
for c in list(ly.each_cell())[:40]:
    print(" ", c.name, "| instances:", c.child_instances())
