#!/usr/bin/env python3

# /// script
# dependencies = [
#   "rich",
#   "typer",
# ]
# ///

from pathlib import Path
import time
import csv
import multiprocessing

import acts
import acts.examples
from acts.examples.simulation import (
    MomentumConfig,
    EtaConfig,
    PhiConfig,
    ParticleConfig,
    addParticleGun,
    addPythia8,
    ParticleSelectorConfig,
    addFatras,
    addGeant4,
    addDigitization,
)
from acts.examples.reconstruction import (
    SeedFinderConfigArg,
    addSeeding,
    TrackSelectorConfig,
    CkfConfig,
    addCKFTracks,
)
from acts.examples.odd import getOpenDataDetector, getOpenDataDetectorDirectory

from typing import Annotated

import typer
import rich
from rich.panel import Panel


geoDir = getOpenDataDetectorDirectory()
oddMaterialMap = geoDir / "data/odd-material-maps.root"
oddDigiConfig = geoDir / "config/odd-digi-smearing-config.json"
oddSeedingSel = geoDir / "config/odd-seeding-config.json"
oddMaterialDeco = acts.IMaterialDecorator.fromFile(oddMaterialMap)

# parser = argparse.ArgumentParser()
# parser.add_argument("outputDir", help="Output directory", type=Path)
# parser.add_argument("--ttbar", help="Use ttbar events", action="store_true")
# parser.add_argument("--geant4", help="Use geant4 simulation", action="store_true")
# args = parser.parse_args()

u = acts.UnitConstants


field = acts.ConstantBField(acts.Vector3(0.0, 0.0, 2.0 * u.T))
rnd = acts.examples.RandomNumbers(seed=42)

app = typer.Typer()

events = 10


@app.command()
def simulate(
    output_dir: Path,
    ttbar: bool = False,
    geant4: bool = False,
    events: Annotated[int, typer.Option("--events", "-n")] = 10,
    threads: Annotated[int, typer.Option("--threads", "-j")] = -1,
    dry_run: Annotated[bool, typer.Option("--dry-run", "-S")] = False,
):
    detector = getOpenDataDetector(odd_dir=geoDir, mdecorator=oddMaterialDeco)
    trackingGeometry = detector.trackingGeometry()

    outputDir = output_dir.resolve()
    outputDir.mkdir(parents=True, exist_ok=True)

    rich.print(
        Panel(
            f"""
Running simulation with output directory {outputDir}
Running with {threads} threads
Running {events} events
    """.strip(),
            title="Config",
        )
    )

    s = acts.examples.Sequencer(
        events=events,
        numThreads=threads,
        outputDir=str(outputDir),
        trackFpes=False,
        # logLevel=acts.logging.WARNING,
    )

    if not ttbar:
        addParticleGun(
            s,
            MomentumConfig(1.0 * u.GeV, 10.0 * u.GeV, transverse=True),
            EtaConfig(-3.0, 3.0, uniform=True),
            PhiConfig(0.0, 360.0 * u.degree),
            ParticleConfig(4, acts.PdgParticle.eMuon, randomizeCharge=True),
            vtxGen=acts.examples.GaussianVertexGenerator(
                mean=acts.Vector4(0, 0, 0, 0),
                stddev=acts.Vector4(
                    0.0125 * u.mm, 0.0125 * u.mm, 55.5 * u.mm, 1.0 * u.ns
                ),
            ),
            multiplicity=50,
            rnd=rnd,
            outputDirRoot=outputDir,
        )
    else:
        addPythia8(
            s,
            hardProcess=["Top:qqbar2ttbar=on"],
            npileup=200,
            vtxGen=acts.examples.GaussianVertexGenerator(
                mean=acts.Vector4(0, 0, 0, 0),
                stddev=acts.Vector4(
                    0.0125 * u.mm, 0.0125 * u.mm, 55.5 * u.mm, 5.0 * u.ns
                ),
            ),
            rnd=rnd,
            outputDirRoot=outputDir,
        )

    if not geant4:
        addFatras(
            s,
            trackingGeometry,
            field,
            preSelectParticles=ParticleSelectorConfig(
                rho=(0.0, 24 * u.mm),
                absZ=(0.0, 1.0 * u.m),
            ),
            postSelectParticles=ParticleSelectorConfig(
                eta=(-3.0, 3.0),
                pt=(150 * u.MeV, None),
                removeNeutral=True,
            ),
            enableInteractions=True,
            outputDirRoot=outputDir,
            rnd=rnd,
        )
    else:
        addGeant4(
            s,
            detector,
            trackingGeometry,
            field,
            preSelectParticles=ParticleSelectorConfig(
                rho=(0.0, 24 * u.mm),
                absZ=(0.0, 1.0 * u.m),
            ),
            postSelectParticles=ParticleSelectorConfig(
                eta=(-3.0, 3.0),
                pt=(150 * u.MeV, None),
                removeNeutral=True,
            ),
            outputDirRoot=outputDir,
            rnd=rnd,
            killVolume=trackingGeometry.worldVolume,
            killAfterTime=25 * u.ns,
        )

    if not dry_run:
        s.run()


@app.command()
def reconstruct(
    input_dir: Annotated[Path, typer.Argument(exists=True, file_okay=False)],
    events: Annotated[int, typer.Option("--events", "-n")] = 10,
    threads: Annotated[int, typer.Option("--threads", "-j")] = -1,
    dry_run: Annotated[bool, typer.Option("--dry-run", "-S")] = False,
):
    detector = getOpenDataDetector(odd_dir=geoDir, mdecorator=oddMaterialDeco)
    trackingGeometry = detector.trackingGeometry()

    inputDir = input_dir.resolve()

    rich.print(
        Panel(
            f"""
Running reconstruction with input directory {inputDir}
Running with {threads} threads
Running {events} events
    """.strip(),
            title="Config",
        )
    )

    s = acts.examples.Sequencer(
        events=events,
        numThreads=threads,
        outputDir=str(inputDir),
        outputTimingFile="timing_reco.csv",
        trackFpes=False,
        # logLevel=acts.logging.WARNING,
    )

    particle_reader = acts.examples.RootParticleReader(
        level=acts.logging.INFO,
        filePath=str(inputDir / "particles.root"),
        outputParticles="particles_input",
    )
    # s.addReader(particle_reader)

    s.addReader(
        acts.examples.BufferedReader(
            level=acts.logging.INFO,
            upstreamReader=particle_reader,
            bufferSize=100,
        )
    )

    # FATRAS wrote only selected particles
    s.addWhiteboardAlias("particles_selected", "particles_input")

    simhit_reader = acts.examples.RootSimHitReader(
        level=acts.logging.INFO,
        filePath=str(inputDir / "hits.root"),
        outputSimHits="simhits",
    )
    # s.addReader(simhit_reader)

    s.addReader(
        acts.examples.BufferedReader(
            level=acts.logging.INFO,
            upstreamReader=simhit_reader,
            bufferSize=100,
        )
    )

    addDigitization(
        s,
        trackingGeometry,
        field,
        digiConfigFile=oddDigiConfig,
        # outputDirRoot=outputDir,
        rnd=rnd,
    )

    addSeeding(
        s,
        trackingGeometry,
        field,
        geoSelectionConfigFile=oddSeedingSel,
        seedFinderConfigArg=SeedFinderConfigArg(
            # r=(33 * u.mm, 200 * u.mm),
            # deltaR=(1 * u.mm, 60 * u.mm),
            # collisionRegion=(-250 * u.mm, 250 * u.mm),
            # z=(-2000 * u.mm, 2000 * u.mm),
            # maxSeedsPerSpM=1,
            # sigmaScattering=5,
            # radLengthPerSeed=0.1,
            minPt=0.9 * u.GeV,
            # impactMax=3 * u.mm,
        ),
        # outputDirRoot=outputDir,
        # outputDirCsv=outputDir,
    )

    addCKFTracks(
        s,
        trackingGeometry,
        field,
        TrackSelectorConfig(
            pt=(1.0 * u.GeV, None),
            absEta=(None, 3.0),
            loc0=(-4.0 * u.mm, 4.0 * u.mm),
            nMeasurementsMin=7,
            maxHoles=2,
            maxOutliers=2,
            maxHolesAndOutliers=4,
        ),
        CkfConfig(
            chi2CutOffMeasurement=9,
            chi2CutOffOutlier=15,
            numMeasurementsCutOff=1,
            seedDeduplication=True,
            stayOnSeed=True,
        ),
        # writeCovMat=True,
        # outputDirCsv=outputDir,
        # outputDirRoot=outputDir,
        # logLevel=acts.logging.VERBOSE,
    )

    if not dry_run:
        s.run()


def get_timing(file) -> float:
    with file.open("r") as fh:
        reader = csv.DictReader(fh)
        t: dict[str, float] = {"total": 0}
        for row in reader:
            for alg, key in [
                ("seeding", "Algorithm:SeedingAlgorithm"),
                ("ckf", "Algorithm:TrackFindingAlgorithm"),
                ("fatras", "Algorithm:FatrasSimulation"),
                ("geant4", "Algorithm:Geant4Simulation"),
                ("sp", "Algorithm:SpacePointMaker"),
            ]:

                if row["identifier"] == key:
                    t[alg] = float(row["time_total_s"])
                t["total"] += float(row["time_total_s"])
        print(f"finished and got times {t}")
        return t["total"]


class Timer:
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.end_time = time.perf_counter()
        self.elapsed_time = self.end_time - self.start_time


@app.command()
def measure(
    input_dir: Annotated[Path, typer.Argument(exists=True, file_okay=False)],
    output_file: Annotated[Path, typer.Option("--output", "-o")] = Path("timing.csv"),
    target_time_per_run: float = 30,
    runs: int = 1,
    threads_max: int = multiprocessing.cpu_count(),
):
    with output_file.open("w") as fh:
        csv_writer = csv.DictWriter(
            fh,
            fieldnames=["threads", "events", "time", "time_per_event_s", "throughput"],
        )
        csv_writer.writeheader()
        fh.flush()

        # Measure initialization time
        timer = Timer()
        with timer:
            reconstruct(input_dir=input_dir, events=0, threads=1)
        init_time = timer.elapsed_time
        print(f"Initialization time: {init_time:.4f}")

        csv_writer.writerow(
            {
                "threads": 1,
                "events": 0,
                "time": init_time,
                "time_per_event_s": float("nan"),
                "throughput": float("nan"),
            }
        )
        fh.flush()

        base_events = 100
        timer = Timer()
        with timer:
            reconstruct(input_dir=input_dir, events=base_events, threads=1)
        total_time = timer.elapsed_time - init_time
        # total_time = get_timing(input_dir / "timing_reco.csv")
        time_per_event_s = total_time / float(base_events)
        events_per_run = int((target_time_per_run - init_time) / time_per_event_s)
        throughput = 1.0 / time_per_event_s

        rich.print(
            Panel(
                "\n".join(
                    [
                        f"Events: {base_events}",
                        f"Time: {total_time:.4f} + {init_time:.4f} (init) = {timer.elapsed_time:.4f}",
                        f"Time per event: {time_per_event_s:.4f}",
                        f"Throughput: {throughput:.4f}",
                        f"New events per run for total time of {target_time_per_run:.4f}s: {events_per_run}",
                    ]
                ),
                title="Initial estimate",
            )
        )

        csv_writer.writerow(
            {
                "threads": 1,
                "events": base_events,
                "time": timer.elapsed_time,
                "time_per_event_s": time_per_event_s,
                "throughput": throughput,
            }
        )
        fh.flush()

        for i in range(2, threads_max + 1):
            total_events = 0
            total_time = 0
            for _ in range(runs):
                events = max(10, i * events_per_run)
                events = max(i * 10, events)
                total_events += events
                with timer:
                    reconstruct(input_dir=input_dir, events=events, threads=i)

                run_time = timer.elapsed_time
                # run_time = get_timing(input_dir / "timing_reco.csv")
                total_time += run_time
            time_per_event_s = float(total_time - runs * init_time) / float(
                total_events
            )
            throughput = 1.0 / time_per_event_s
            # events_per_run = int(target_time_per_run / time_per_event_s)

            rich.print(
                Panel(
                    "\n".join(
                        [
                            f"Finished run {i}",
                            f"Events: {total_events}",
                            f"Time: {total_time:.4f} + {runs*init_time:.4f} (init) = {timer.elapsed_time:.4f}",
                            f"Time per event: {time_per_event_s:.4f}",
                            f"Throughput: {throughput:.4f}",
                            # f"New events per run for total time of {target_time_per_run}s: {events_per_run}",
                        ]
                    ),
                    title=f"Results for thread count: {i}",
                )
            )

            csv_writer.writerow(
                {
                    "threads": i,
                    "events": total_events,
                    "time": total_time,
                    "time_per_event_s": time_per_event_s,
                    "throughput": throughput,
                }
            )
            fh.flush()


app()
