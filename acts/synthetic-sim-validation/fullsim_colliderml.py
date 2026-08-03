"""Extract ODD full-simulation distributions from a ColliderML shard.

ColliderML is the OpenDataDetector's own full-simulation release, Geant4 through
Key4hep on the same ODD geometry the synthetic ODD layout stands in for, so it is
the reference the ODD preset should be judged against. The dataset lives on
HuggingFace as `CERN/ColliderML-Release-1`, one subset per (channel, pile-up,
object) with a hundred events per shard.

    https://huggingface.co/datasets/CERN/ColliderML-Release-1

Only the `particles` and `tracker_hits` tables are read; `calo_hits` and the
reconstructed `tracks` have no counterpart in a space point generator. Reading
needs `pyarrow`, which in the ACTS spack environment has to be helped along - see
the README.
"""

from __future__ import annotations

import numpy as np
import pyarrow.parquet as pq

import sample

DATASET = "CERN/ColliderML-Release-1"

#: One shard is a hundred events, which is far more than the comparison needs.
SHARD = "train-00000-of-01000.parquet"

#: The ODD pixel detector: negative endcap, barrel, positive endcap. The dataset
#: numbers volumes as the ODD geometry does, and the `detector` column is a
#: parallel enumeration of the same nine volumes, so either would do.
PIXEL_VOLUMES = (16, 17, 18)

PARTICLE_COLUMNS = ["event_id", "particle_id", "charge",
                    "vx", "vy", "vz", "px", "py", "pz", "primary"]
HIT_COLUMNS = ["event_id", "x", "y", "z", "particle_id", "volume_id"]


def _shard(channel: str, pileup: str, table: str, local: str | None) -> str:
    """Locate one parquet shard, downloading it if it is not there already.

    @param channel the physics channel, e.g. "ttbar"
    @param pileup the pile-up variant, "pu0" or "pu200"
    @param table "particles" or "tracker_hits"
    @param local a directory holding `<channel>_<pileup>_<table>/<shard>`, or
           None to fetch from HuggingFace into the usual cache
    @return the path to the shard
    """
    subset = f"{channel}_{pileup}_{table}"
    if local is not None:
        from pathlib import Path

        candidates = [Path(local) / subset / SHARD, Path(local) / f"{subset}.parquet"]
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
        raise FileNotFoundError("no %s shard under %s, looked for %s"
                                % (subset, local, [str(c) for c in candidates]))

    # hf_hub_download caches by content, so asking again is free
    from huggingface_hub import hf_hub_download

    return hf_hub_download(DATASET, f"data/{subset}/{SHARD}", repo_type="dataset")


def _hits_per_particle(hit_particle_id, particle_id):
    """Count the pixel hits each particle left.

    @param hit_particle_id the particle each selected hit belongs to
    @param particle_id the particles to count for
    @return the count per entry of `particle_id`
    """
    if len(hit_particle_id) == 0:
        return np.zeros(len(particle_id), dtype=np.int32)
    ids, counts = np.unique(hit_particle_id, return_counts=True)
    # `ids` is sorted, so one search places every particle at once
    where = np.searchsorted(ids, particle_id)
    inside = where < len(ids)
    clamped = np.where(inside, where, 0)
    found = inside & (ids[clamped] == particle_id)
    return np.where(found, counts[clamped], 0).astype(np.int32)


def load(channel: str = "ttbar", pileup: str = "pu200", num_events: int = 20,
         local: str | None = None, min_pt_gev: float = 0.1,
         max_abs_eta: float = 4.0, skip_events: int = 0) -> sample.Sample:
    """Read a ColliderML shard and return the distributions to compare against.

    The selection mirrors the ITk one: charged particles inside the generator's
    acceptance that leave at least one pixel space point. Without the hit
    requirement the sample is dominated by the pile-up particles that never reach
    the detector, and by the neutrals, which a space point generator does not
    model at all.

    @param channel the physics channel
    @param pileup the pile-up variant, "pu0" or "pu200"
    @param num_events how many events to read, at most a shard's hundred
    @param skip_events how many to pass over first, so that a fit and the
           validation of it can be given different events
    @param local a directory of already-downloaded shards, or None to fetch them
    @param min_pt_gev the momentum threshold in GeV
    @param max_abs_eta the pseudorapidity acceptance
    @return the distributions
    """
    particles = pq.ParquetFile(_shard(channel, pileup, "particles", local))
    hits = pq.ParquetFile(_shard(channel, pileup, "tracker_hits", local))

    out = sample.Sample()
    # one event per batch, so a shard is never held in memory in full
    batches = zip(particles.iter_batches(batch_size=1, columns=PARTICLE_COLUMNS),
                  hits.iter_batches(batch_size=1, columns=HIT_COLUMNS))
    seen = 0
    for particle_batch, hit_batch in batches:
        if out.num_events >= num_events:
            break
        seen += 1
        if seen <= skip_events:
            continue
        _load_event(out,
                    particle_batch.to_pylist()[0], hit_batch.to_pylist()[0],
                    min_pt_gev, max_abs_eta)

    if out.num_events == 0:
        raise RuntimeError("read no events at all")
    return out.finish()


def _load_event(out: sample.Sample, particles, hits, min_pt_gev: float,
                max_abs_eta: float) -> None:
    if particles["event_id"] != hits["event_id"]:
        raise RuntimeError("the two shards disagree on the event order, %s vs %s"
                           % (particles["event_id"], hits["event_id"]))

    volume = np.asarray(hits["volume_id"])
    is_pixel = np.isin(volume, PIXEL_VOLUMES)
    sp_x = np.asarray(hits["x"], dtype=np.float32)[is_pixel]
    sp_y = np.asarray(hits["y"], dtype=np.float32)[is_pixel]
    sp_z = np.asarray(hits["z"], dtype=np.float32)[is_pixel]

    particle_id = np.asarray(particles["particle_id"])
    hit_particle = np.asarray(hits["particle_id"])[is_pixel]
    num_hits = _hits_per_particle(hit_particle, particle_id)

    # every ColliderML hit carries a particle link, so the split is a lookup;
    # a link to a particle outside the table counts as not primary
    is_generator = np.asarray(particles["primary"], dtype=bool)
    order = np.argsort(particle_id)
    where = np.searchsorted(particle_id[order], hit_particle)
    inside = where < len(particle_id)
    clamped = np.where(inside, where, 0)
    found = inside & (particle_id[order][clamped] == hit_particle)
    sp_primary = np.where(found, is_generator[order][clamped], False)

    charge = np.asarray(particles["charge"])
    px = np.asarray(particles["px"])
    py = np.asarray(particles["py"])
    pz = np.asarray(particles["pz"])
    pt = np.hypot(px, py)
    with np.errstate(divide="ignore", invalid="ignore"):
        eta = np.arcsinh(np.where(pt > 0, pz / pt, np.nan))

    selected = (
        (np.abs(charge) > 0.5)
        & (pt > min_pt_gev)
        & np.isfinite(eta)
        & (np.abs(eta) < max_abs_eta)
        & (num_hits > 0)
    )

    vx = np.asarray(particles["vx"])[selected]
    vy = np.asarray(particles["vy"])[selected]
    vz = np.asarray(particles["vz"])[selected]
    # The shard carries `perigee_d0` and `perigee_z0` of its own, but they are
    # NaN for a fifth of the charged particles above 100 MeV, and their d0 has
    # the opposite sign to the one used here. Where they are finite they agree
    # with this in magnitude.
    # the shard's momenta are already in GeV, which is what `perigee` needs to
    # turn them into a radius of curvature
    phi, d0, z0 = sample.perigee(vx, vy, vz,
                                 px[selected], py[selected], pz[selected],
                                 charge[selected])

    out.add_event(
        sp_x=sp_x, sp_y=sp_y, sp_z=sp_z, sp_primary=sp_primary,
        pt=pt[selected],
        eta=eta[selected],
        phi=phi.astype(np.float32),
        d0=d0.astype(np.float32),
        z0=z0.astype(np.float32),
        prod_r=np.hypot(vx, vy),
        prod_z=vz,
        # `primary` is the dataset's own generator/secondary flag, so the ITk
        # loader's barcode convention has no counterpart to reproduce here
        primary=np.asarray(particles["primary"], dtype=bool)[selected],
        num_hits=num_hits[selected],
    )
