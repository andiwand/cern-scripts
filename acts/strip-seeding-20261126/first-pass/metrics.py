def selections(p):
    uid,pdg,status,q,pt,eta,r,z,nc,nsp,nlayers,nlsp,nllayers=p[:13]
    primary=status==1 and q!=0 and 0<=r<300 and abs(eta)<4 and pt>1000
    return {'primary':primary,'barrel':primary and abs(eta)<.6,
      'seedable':primary and nsp>=3 and nlayers>=3,
      'common':primary and nsp>=3 and nlayers>=3 and nlsp>=3 and nllayers>=3,
      'prompt':primary and r<1 and nsp>=3 and nlayers>=3}
