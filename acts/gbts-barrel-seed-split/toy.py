# Toy: genuine eta=0 tracks through ITk pixel barrel; how often does the GBTS
# seed-split curvature check (maxInvRadDiff = 7e-6 /mm in 1/(2R)) fail?
import numpy as np
rng=np.random.default_rng(1)
R=np.array([34.,99.,160.,228.,291.])  # mm
B=2.0
def estc(p):  # ACTS estimateCurvature: conformal, origin at last point -> 1/(2R) [1/mm]
    x0,y0=p[2]; r0=np.hypot(x0,y0); c,s=x0/r0,y0/r0
    u=[];v=[]
    for k in range(2):
        dx,dy=p[k][0]-x0,p[k][1]-y0; r2=1/(dx*dx+dy*dy)
        u.append((dx*c+dy*s)*r2); v.append((-dx*s+dy*c)*r2)
    A=(v[0]-v[1])/(u[0]-u[1]); Bc=v[1]-A*u[1]; return Bc/np.sqrt(1+A*A)
def track(pt,x0=0.015,sig=0.010,ms=True):
    # step a helix through layers, kick direction at each layer
    q=1; rad=pt/(0.3*B)*1000  # mm
    pos=np.zeros(2); phi=0.0; pts=[]
    for i,r in enumerate(R):
        # propagate on a circle from pos with direction phi to radius r (small steps)
        while np.hypot(*pos)<r:
            ds=0.5; phi+=q*ds/rad; pos=pos+ds*np.array([np.cos(phi),np.sin(phi)])
        if ms:
            th0=13.6e-3/pt*np.sqrt(x0)*(1+0.038*np.log(x0)); phi+=rng.normal(0,th0)
        n=np.array([-pos[1],pos[0]])/np.hypot(*pos)
        pts.append(pos+rng.normal(0,sig)*n)
    return pts
def split(vN,cut=7e-6):
    n=len(vN); t0=[vN[0],vN[n//2],vN[n-1]]
    d1=vN[1:]; t1=[d1[0],d1[(n-1)//2],d1[n-2]]
    d2=[vN[k] for k in range(n) if k!=n//2]; t2=[d2[0],d2[(n-1)//2],d2[n-2]]
    c=[estc(t) for t in (t0,t1,t2)]
    return not (abs(c[1]-c[0])<cut and abs(c[2]-c[0])<cut and abs(c[2]-c[1])<cut)
N=2000
print("pT  5SP-split  4SP(L1-L4)-split  5SP-split(noMS)  5SP-split(cut x3)")
for pt in [0.9,1.0,1.5,2,3,5,10,50]:
    a=b=c=d=0
    for _ in range(N):
        t=track(pt); a+=split(t); b+=split(t[1:]); d+=split(t,3*7e-6)
        c+=split(track(pt,ms=False))
    print(f"{pt:4} {a/N:9.2%} {b/N:12.2%} {c/N:12.2%} {d/N:12.2%}")
