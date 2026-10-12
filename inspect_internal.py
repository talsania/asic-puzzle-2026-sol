import klayout.db as db, collections
ly = db.Layout(); ly.read("puzzle.gds")
top = ly.top_cells()[0]

for name in ["INTERNAL_3", "INTERNAL_7"]:
    c = ly.cell(name)
    bb = c.bbox().to_dtype(ly.dbu)
    print(f"\n=== {name}: size {bb.width():.2f} x {bb.height():.2f} um, "
          f"child instances: {collections.Counter(i.cell.name for i in c.each_inst())}")
    for li in ly.layer_indexes():
        info = ly.get_info(li)
        n = sum(1 for _ in db.RecursiveShapeIterator(ly, c, li).each())
        txt = [s.text.string for s in c.shapes(li).each() if s.is_text()]
        if n:
            print(f"  {info.layer}/{info.datatype}: {n} shapes", f" texts={txt}" if txt else "")
    uses = [(i.trans.disp.x, i.trans.disp.y) for i in top.each_inst() if i.cell.name == name]
    print("  placed at (first 5):", uses[:5])
