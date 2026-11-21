# Single-particle gun for the scattering-tail study, steered by env: TAILGUN_PID (|pdg|, both charges), TAILGUN_PT (GeV), TAILGUN_ETA (max |eta|).
import os
from AthenaConfiguration.ComponentAccumulator import ComponentAccumulator


def TailGunCfg(flags, cfg=None):
    import ParticleGun as PG
    from GeneratorConfig.Sequences import EvgenSequence, EvgenSequenceFactory
    from GeneratorConfig.GeneratorInfoSvcConfig import GeneratorInfoSvcCfg
    ca = ComponentAccumulator(EvgenSequenceFactory(EvgenSequence.Generator))
    ca.merge(GeneratorInfoSvcCfg(flags, Generators=["ParticleGun"]), sequenceName=EvgenSequence.Generator.value)
    pid = int(os.environ.get("TAILGUN_PID", "13"))
    eta = float(os.environ.get("TAILGUN_ETA", "4.0"))
    pg = PG.ParticleGun(randomStream="SINGLE", randomSeed=flags.Random.SeedOffset)
    pg.sampler.pid = PG.CyclicSeqSampler([-pid, pid])
    pg.sampler.mom = PG.PtEtaMPhiSampler(pt=1000 * float(os.environ.get("TAILGUN_PT", "10")), eta=[-eta, eta])
    ca.addEventAlgo(pg)
    if cfg is None:
        return ca
    cfg.merge(ca)
