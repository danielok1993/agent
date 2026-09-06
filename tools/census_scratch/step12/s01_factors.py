import sys, time
sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch")
import harness as H
pages = H.load("s01")
for p in pages:
    for f in (p.scale_factor, 50.0 / 92.2):
        t = time.time()
        ents, extras = H.run(p, factor=f)
        sc = H.score("s01", p.page_number, ents)
        print(f"s01 p{p.page_number} f={f:.4f} counts={sc['counts']} lost={len(sc['lost'])} retFP={len(sc['returned_fps'])} unrev={len(sc['unreviewed'])} ({time.time()-t:.0f}s)")
        for l in sc["lost"]:
            print("   LOST", l)
        for u in sc["unreviewed"]:
            print("   UNREV", u)
        n_rooms = sum(1 for e in ents if e["entity_type"] == "room")
        n_doors = sum(1 for e in ents if e["entity_type"] == "door")
        n_win = sum(1 for e in ents if e["entity_type"] == "window")
        print(f"   emitted doors={n_doors} windows={n_win} rooms={n_rooms}")
