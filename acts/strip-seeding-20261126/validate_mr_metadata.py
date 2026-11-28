from pathlib import Path
import shlex,subprocess
root=Path('/home/astefl/source/acts/acts-athena-ci');out=root/'studies/strip-seeding-mr-20261126'
old=root/'athena-strip-seeding/Tracking/Acts/ActsPatternRecognition';new=root/'athena-strip-seeding-mr/Tracking/Acts/ActsPatternRecognition'
args=shlex.split((out/'compile-command.txt').read_text());args=args[args.index('--')+1:]
args=[s.replace(str(old),str(new)) for s in args]
for flag,suffix in [('-o','GbtsSeedingTool.o'),('-MF','GbtsSeedingTool.d'),('-MT','GbtsSeedingTool.o')]:args[args.index(flag)+1]=str(out/suffix)
with (out/'metadata-compile.log').open('w') as log:subprocess.run(args,cwd=root/'athena-build-strip-seeding',stdout=log,stderr=subprocess.STDOUT,check=True)
unit=[];i=0
while i<len(args):
 if args[i] in ['-MF','-MT']:i+=2;continue
 if args[i] in ['-c','-MD']:i+=1;continue
 if args[i]=='-o':unit.extend(['-o',str(out/'GbtsConnectionTuningTest')]);i+=2;continue
 unit.append(str(Path('/home/astefl/scripts/acts/strip-seeding-20261126/connection_metadata_probe.cxx')) if args[i].endswith('/src/GbtsSeedingTool.cxx') else args[i]);i+=1
with (out/'metadata-check.log').open('w') as log:
 subprocess.run(unit,cwd=root/'athena-build-strip-seeding',stdout=log,stderr=subprocess.STDOUT,check=True)
 subprocess.run([str(out/'GbtsConnectionTuningTest'),str(out/'connection-fixture.txt')],stdout=log,stderr=subprocess.STDOUT,check=True)
print('Exact MR GBTS source compiles; exact MR connection test passes with the release compiler and flags.')
