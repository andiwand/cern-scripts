import sys, collections, numpy as np, awkward as ak, uproot
ID = ["vertex_primary", "vertex_secondary", "particle", "generation", "sub_particle"]
names = {0: "Alive", 1: "KilledInteraction", 2: "KilledVolumeExit", 3: "KilledTime", 4: "KilledSecondaryParticle"}
for d in sys.argv[1:]:
    A = uproot.open(f"{d}/particles_simulation.root")["particles"].arrays(["event_id", "outcome", "q", "p", "number_of_hits", "particle_type"] + ID)
    oc = ak.to_numpy(ak.flatten(A.outcome)); q = ak.to_numpy(ak.flatten(A.q)); nh = ak.to_numpy(ak.flatten(A.number_of_hits))
    p = ak.to_numpy(ak.flatten(A.p)); pdg = ak.to_numpy(ak.flatten(A.particle_type)); gen = ak.to_numpy(ak.flatten(A.generation))
    nev = len(A)
    print(f"{d}: {len(oc)/nev:.0f} particles/event")
    c = collections.Counter(oc.tolist())
    print("  outcome (all):", {names.get(k, k): v for k, v in sorted(c.items())})
    w = nh > 0
    c = collections.Counter(oc[w].tolist())
    print("  outcome (particles with hits):", {names.get(k, k): v for k, v in sorted(c.items())})
    # last hit of each particle: radius and time
    h = uproot.open(f"{d}/hits.root")["hits"].arrays(["event_id", "tx", "ty", "tz", "tt", "volume_id"] + [f"barcode_{i}" for i in ID], library="np")
    hk = list(zip(h["event_id"].tolist(), *[h[f"barcode_{i}"].tolist() for i in ID]))
    last = {}
    for k, r, t, z in zip(hk, np.hypot(h["tx"], h["ty"]), h["tt"], h["tz"]):
        if k not in last or t > last[k][1]: last[k] = (r, t, abs(z))
    ev = ak.to_numpy(ak.flatten(ak.broadcast_arrays(A.event_id, A.q)[0]))
    pk = list(zip(ev.tolist(), *[ak.to_numpy(ak.flatten(A[i])).tolist() for i in ID]))
    for code in (1, 3):
        rs = [last[k] for k, o in zip(pk, oc) if o == code and k in last]
        if rs:
            r = np.array([x[0] for x in rs]); t = np.array([x[1] for x in rs]); z = np.array([x[2] for x in rs])
            print(f"  {names[code]} with hits: {len(rs)}, last hit r<200 mm and |z|<1 m: {100*np.mean((r<200)&(z<1000)):.0f}%, last hit inside r<1 m: {100*np.mean(r<1000):.0f}%, last hit time median {np.median(t):.1f} ns")
    # hits per particle of loopers
