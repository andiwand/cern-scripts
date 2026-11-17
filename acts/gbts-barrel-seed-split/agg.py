import sys,re,collections
rows=collections.defaultdict(lambda: collections.defaultdict(lambda:[0]*12))
tot=collections.defaultdict(lambda:[0,0,0])
for l in open(sys.argv[1]):
    f=l.split()
    tag=f[0]
    if 'efficiency=' in l:
        d=dict(x.split('=') for x in f[2:]); tot[tag][0]+=int(d['seeds']); tot[tag][1]+=int(d['trueSeeds']); continue
    if f[3]=='|eta|': continue
    b=f[3]; s3,e3,s4,e4,o3,dup=map(float,f[4:10]); sz=list(map(int,f[10].split('/')))
    r=rows[tag][b]; m=e3*s3
    r[0]+=s3; r[1]+=m; r[2]+=o3*m; r[3]+=dup*m
    for i in range(4): r[4+i]+=sz[i]
for tag in rows:
    print(f"== {tag}: seeds/evt {tot[tag][0]/20:.0f}  true/evt {tot[tag][1]/20:.0f}")
    print("|eta|      seedable   eff     only3SP  dup     sizes 3/4/5/6+")
    S=M=0
    for b,r in rows[tag].items():
        S+=r[0];M+=r[1]
        print(f"{b:9} {r[0]:8.0f} {r[1]/r[0]:7.4f} {r[2]/max(r[1],1):7.4f} {r[3]/max(r[1],1):7.4f}  {r[4]}/{r[5]}/{r[6]}/{r[7]}")
    print(f"all       {S:8.0f} {M/S:7.4f}")
