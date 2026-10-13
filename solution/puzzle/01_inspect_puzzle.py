import klayout.db as db, collections

ly = db.Layout()
ly.read("puzzle.gds")
print("dbu:", ly.dbu)
print("top cells:", [c.name for c in ly.top_cells()])
top = ly.top_cells()[0]
print("bbox (um):", top.bbox().to_dtype(ly.dbu))
print("cells:", ly.cells(), " top-level instances:", top.child_instances())

print("\nLayers (flattened shape counts):")
for li in ly.layer_indexes():
    i = ly.get_info(li)
    n = top.begin_shapes_rec(li).each().__class__ and sum(1 for _ in top.begin_shapes_rec(li).each())
    print(f"  {i.layer}/{i.datatype}  shapes={n}")

print("\nCell types used by the top cell:")
cnt = collections.Counter(inst.cell.name for inst in top.each_inst())
for k, v in cnt.most_common():
    print(f"  {v:5d}  {k}")

print("\nTop-level texts:")
for li in ly.layer_indexes():
    i = ly.get_info(li)
    for sh in top.shapes(li).each():
        if sh.is_text():
            print(f"  {i.layer}/{i.datatype}  {sh.text.string!r}  ({sh.text.x},{sh.text.y})")
