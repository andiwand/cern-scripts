'use strict';
const charts=JSON.parse(document.getElementById('plot-data').textContent), ns='http://www.w3.org/2000/svg';
function node(tag,attrs={},text){const el=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))el.setAttribute(k,v);if(text!==undefined)el.textContent=text;return el;}
function download(content,type,name){const u=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);}
function draw(chart,index){
 const box=document.createElement('article');box.className='figure';const h=document.createElement('h3');h.textContent=chart.title;box.append(h);
 const height=Math.max(530,480+chart.series.length*20);
 const svg=node('svg',{viewBox:`0 0 920 ${height}`,'font-family':'system-ui,sans-serif',role:'img','aria-label':chart.title});svg.append(node('title',{},chart.title));box.append(svg);
 const legend=document.createElement('div');legend.className='legend';const visible=chart.series.map(()=>true);box.append(legend);
 chart.series.forEach((s,i)=>{const l=document.createElement('label'),c=document.createElement('input');c.type='checkbox';c.checked=true;c.onchange=()=>{visible[i]=c.checked;render();};l.append(c,document.createTextNode(s.label));l.style.color=s.color;legend.append(l);});
 const readout=document.createElement('p');readout.className='caption';readout.setAttribute('aria-live','polite');readout.textContent='Hover or focus a point for exact values.';box.append(readout);
 const cap=document.createElement('p');cap.className='caption';cap.textContent=chart.caption;box.append(cap);
 const save=document.createElement('button');save.textContent='Save SVG';save.onclick=()=>download(new XMLSerializer().serializeToString(svg),'image/svg+xml',`figure-${index+1}.svg`);box.append(save);
 const extra=document.getElementById('more-figures');(extra&&index>=2?extra:document.getElementById('figures')).append(box);
 function render(){
  svg.replaceChildren(node('title',{},chart.title),node('rect',{width:920,height,fill:'white'}));const all=chart.series.flatMap(s=>s.points).filter(p=>Number.isFinite(p.x)&&Number.isFinite(p.y));
  if(!all.length)return;let xmin=Math.min(...all.map(p=>p.x)),xmax=Math.max(...all.map(p=>p.x)),ymin=Math.min(...all.map(p=>p.y-(p.error||0))),ymax=Math.max(...all.map(p=>p.y+(p.error||0)));
  const dx=(xmax-xmin)||Math.max(.01,Math.abs(xmin)*.01),dy=(ymax-ymin)||Math.max(.001,Math.abs(ymin)*.1);xmin-=dx*.1;xmax+=dx*.1;ymin=ymin>=0?Math.max(0,ymin-dy*.14):ymin-dy*.14;ymax+=dy*.16;
  const X=x=>90+(x-xmin)/(xmax-xmin)*795,Y=y=>378-(y-ymin)/(ymax-ymin)*338;
  for(let i=0;i<=5;i++){let x=xmin+(xmax-xmin)*i/5,y=ymin+(ymax-ymin)*i/5;
   svg.append(node('line',{x1:X(x),x2:X(x),y1:40,y2:378,stroke:'#e1e6eb'}),node('text',{x:X(x),y:400,'text-anchor':'middle','font-size':13,fill:'#425363'},Number(x.toPrecision(5))),node('line',{x1:90,x2:885,y1:Y(y),y2:Y(y),stroke:'#e1e6eb'}),node('text',{x:80,y:Y(y)+4,'text-anchor':'end','font-size':13,fill:'#425363'},Number(y.toPrecision(4))));}
  svg.append(node('text',{x:490,y:438,'text-anchor':'middle','font-size':15,fill:'#23333d'},chart.xlabel),node('text',{transform:'translate(20 210) rotate(-90)','text-anchor':'middle','font-size':15,fill:'#23333d'},chart.ylabel));
  if(ymin<0&&ymax>0)svg.append(node('line',{x1:90,x2:885,y1:Y(0),y2:Y(0),stroke:'#79868d','stroke-dasharray':'4 4'}));
  chart.series.forEach((s,i)=>{if(!visible[i])return;svg.append(node('line',{x1:90,x2:110,y1:468+i*20,y2:468+i*20,stroke:s.color,'stroke-width':3}),node('text',{x:118,y:472+i*20,'font-size':13,fill:s.color},s.label));const points=s.points.filter(p=>Number.isFinite(p.x)&&Number.isFinite(p.y)).sort((a,b)=>a.x-b.x);
   svg.append(node('polyline',{points:points.map(p=>`${X(p.x)},${Y(p.y)}`).join(' '),fill:'none',stroke:s.color,'stroke-width':2}));
   points.forEach(p=>{if(p.error){svg.append(node('line',{x1:X(p.x),x2:X(p.x),y1:Y(p.y-p.error),y2:Y(p.y+p.error),stroke:s.color,'stroke-width':1.5}));for(const y of [p.y-p.error,p.y+p.error])svg.append(node('line',{x1:X(p.x)-4,x2:X(p.x)+4,y1:Y(y),y2:Y(y),stroke:s.color}));}const label=`${s.label}: ${chart.xlabel} ${p.x.toPrecision(6)}; ${chart.ylabel} ${p.y.toPrecision(6)}. ${p.label||''}`;const c=node('circle',{cx:X(p.x),cy:Y(p.y),r:5,fill:s.color,tabindex:0,'aria-label':label});c.append(node('title',{},label));c.addEventListener('focus',()=>{readout.textContent=label;});c.addEventListener('mouseenter',()=>{readout.textContent=label;});svg.append(c);});});
 }
 render();
}
charts.forEach(draw);document.getElementById('data').onclick=()=>download(JSON.stringify(charts,null,2),'application/json','scattering-tail-plots.json');
