import klayout.db as db
ly = db.Layout(); ly.read("puzzle.gds"); top = ly.top_cells()[0]
row = sorted((i.trans.disp.x, i.cell.name) for i in top.each_inst() if i.cell.name.startswith("INTERNAL"))
for x, n in row: print(x, n)
