#!/usr/bin/env python3
"""Count changed physical code lines, including declarations/imports/build glue."""
import collections
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
ROOT=Path('/home/astefl/source/acts/acts-athena-ci/athena-native-pixel-nn')
BASE='41da040949efeca5de0e5adbd84054868a5165c6'
OUT=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT.parent/'run/native-pixel-nn/loc.json'
def git(*args):
    return subprocess.check_output(['git','-C',str(ROOT),*args],text=True,stderr=subprocess.DEVNULL)
def code_lines(text,suffix):
    lines=text.splitlines()
    if suffix in ('.h','.cxx','.icc'):
        text=re.sub(r'/\*.*?\*/',lambda m:'\n'*m.group().count('\n'),text,flags=re.S)
        return {i for i,s in enumerate(text.splitlines(),1) if s.split('//')[0].strip()}
    return {i for i,s in enumerate(lines,1) if s.strip() and not s.lstrip().startswith('#')}
def test_build_lines(text):
    result=set();active=False
    for i,s in enumerate(text.splitlines(),1):
        if 'atlas_add_test' in s:active=True
        if active:result.add(i)
        if active and s.rstrip().endswith(')'):active=False
    return result
files={};totals=collections.defaultdict(lambda:dict(added=0,removed=0))
for path in git('diff',BASE,'--name-only').splitlines():
    suffix=Path(path).suffix
    if suffix not in ('.h','.cxx','.icc','.py','.txt'):continue
    current=(ROOT/path).read_text()
    try:previous=git('show',BASE+':'+path)
    except subprocess.CalledProcessError:previous=''
    masks={'+':code_lines(current,suffix),'-':code_lines(previous,suffix)}
    cmake_masks={'+':test_build_lines(current),'-':test_build_lines(previous)}
    base='glue'
    if path.endswith('NativePixelClusterNNFromOnnx.cxx'):base='conversion'
    elif Path(path).name in ('NativePixelClusterNN.cxx','NativePixelClusterNN.h','NativePixelClusterNNKernel.icc','NativePixelClusterNNBaseline.cxx','NativePixelClusterNNAvx2.cxx','NativePixelClusterNNConstants.h','PixelClusterNNLayout.h'):base='inference'
    elif '/test/' in path:base='tests'
    counts=collections.defaultdict(lambda:dict(added=0,removed=0))
    old=new=0
    for line in git('diff',BASE,'--unified=0','--',path).splitlines():
        match=re.match(r'@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@',line)
        if match:old,new=map(int,match.groups());continue
        sign=line[:1]
        if sign not in '+-' or line.startswith(('+++','---')):continue
        index=new if sign=='+' else old
        if index in masks[sign]:
            category='tests' if Path(path).name=='CMakeLists.txt' and index in cmake_masks[sign] else base
            if Path(path).name=='NativePixelClusterNN.cxx':
                source = current if sign=='+' else previous
                dispatcher = next(i for i,line in enumerate(source.splitlines(),1)
                                  if line.startswith('void NativePixelClusterNN::infer('))
                category = 'conversion' if index < dispatcher else 'inference'
            key='added' if sign=='+' else 'removed'
            counts[category][key]+=1;totals[category][key]+=1
        if sign=='+':new+=1
        else:old+=1
    files[path]={'sha256':hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),'counts':dict(counts)}
for row in totals.values():row['net']=row['added']-row['removed']
result={'base':BASE,
        'metric':'Changed nonblank, noncomment physical lines; includes headers, imports, build/configuration and tests. Added includes replacement lines; net subtracts removed lines.',
        'excludes':'Documentation and external validation/benchmark scripts; no generated code or embedded learned weights.',
        'totals':dict(totals),'files':files}
OUT.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result['totals'],indent=2))
