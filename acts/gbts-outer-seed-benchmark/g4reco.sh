#!/bin/zsh
source /Users/andreas/cern/source/acts/acts/dev3/activate.sh >/dev/null 2>&1
cd /private/tmp/claude-501/-Users-andreas-cern-source-acts-acts-dev3/454db880-38eb-4c1d-963a-d16b7952c81c/scratchpad
UV="env -i HOME=$HOME PATH=/opt/homebrew/bin:/usr/bin:/bin uv run --no-project --with uproot --with awkward --with numpy python"
mkdir -p g4_pu200
hadd -f g4_pu200/hits.root g4_part{0,1,2,3,4}/hits.root > /dev/null || { echo "hadd hits failed"; exit 1; }
hadd -f g4_pu200/particles_simulation.root g4_part{0,1,2,3,4}/particles_simulation.root > /dev/null || { echo "hadd particles failed"; exit 1; }
out=g4rev_pu200
mkdir -p $out
ln -sf ../g4_pu200/hits.root $out/hits.root
ln -sf ../g4_pu200/particles_simulation.root $out/particles_simulation.root
V="inner_outward outer_outward outer_inward inner_outward_chi30 outer_outward_chi30 outer_inward_chi30 outer_inward_notrim"
python memrun.py run_variants.py --input g4_pu200 --output $out --ttbar --events 40 --jobs 8 --digi geometric --variants ${=V} > $out.log 2> $out.err || { echo "reco failed"; tail -5 $out.err; exit 1; }
grep MEMRUN $out.err
python eff.py $out > /dev/null 2>&1
eval $UV analyze.py $out > /dev/null 2>$out.analyze.err || echo "analysis failed"
eval $UV fate.py $out inner_outward outer_outward inner_outward outer_inward inner_outward_chi30 outer_outward_chi30 inner_outward_chi30 outer_inward_chi30 > $out.fate.txt 2>&1
eval $UV l0diag.py $out outer_inward_notrim ambi > $out.diag.txt 2>&1
find $out -name "trackstates_*_ckf.root" -delete
echo "$out done $(date +%T) $(du -sh $out | cut -f1)"
