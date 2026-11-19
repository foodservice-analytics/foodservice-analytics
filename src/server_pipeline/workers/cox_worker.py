"""Ridge Cox PH (Breslow ties) executed on YT; Python stdlib only."""
import json,sys,math
from collections import Counter,defaultdict

def invert(a):
 n=len(a);rows=[list(a[i])+[float(i==j) for j in range(n)] for i in range(n)]
 for col in range(n):
  pivot=max(range(col,n),key=lambda i:abs(rows[i][col]));rows[col],rows[pivot]=rows[pivot],rows[col]
  if abs(rows[col][col])<1e-12:raise ValueError('Singular information matrix')
  scale=rows[col][col];rows[col]=[v/scale for v in rows[col]]
  for i in range(n):
   if i!=col:
    scale=rows[i][col]
    rows[i]=[x-scale*y for x,y in zip(rows[i],rows[col])]
 return [r[n:] for r in rows]

def fit(rows,ridge=1.,max_iterations=60):
 cats=sorted({r['category'] for r in rows});refcat='Кафе' if 'Кафе' in cats else cats[0];cats=[c for c in cats if c!=refcat]
 top=[d for d,n in Counter(r['district'] for r in rows).most_common(5)]
 refdist='Центральный район' if 'Центральный район' in top else top[0]
 dists=[d for d in top if d!=refdist]+['Другие районы']
 names=['Сетевое заведение','Конкуренты в 300 м: +10']+['Категория: '+c for c in cats]+['Район: '+d for d in dists]
 data=[]
 for r in rows:
  dist=r['district'] if r['district'] in top else 'Другие районы'
  x=[float(r['ownership']=='chain'),float(r['competitors_300m'])/10.]+[float(r['category']==c) for c in cats]+[float(dist==d) for d in dists]
  data.append((int(r['duration']),int(r['event']),x))
 data.sort(key=lambda r:r[0],reverse=True);groups=[]
 for t,event,x in data:
  if not groups or groups[-1][0]!=t:groups.append((t,[]))
  groups[-1][1].append((event,x))
 p=len(names)
 def evaluate(beta):
  s0=0.;s1=[0.]*p;s2=[[0.]*p for i in range(p)];ll=0.;g=[-ridge*b for b in beta];info=[[ridge*float(i==j) for j in range(p)] for i in range(p)]
  for time,group in groups:
   d=0.;evx=[0.]*p;eveta=0.
   for event,x in group:
    eta=sum(b*v for b,v in zip(beta,x));w=math.exp(max(-40.,min(40.,eta)))
    s0+=w
    for i in range(p):
     s1[i]+=w*x[i]
     for j in range(p):s2[i][j]+=w*x[i]*x[j]
    if event:
     d+=1;eveta+=eta
     for i in range(p):evx[i]+=x[i]
   if d:
    ll+=eveta-d*math.log(s0)
    for i in range(p):
     g[i]+=evx[i]-d*s1[i]/s0
     for j in range(p):info[i][j]+=d*(s2[i][j]/s0-s1[i]*s1[j]/s0**2)
  ll-=ridge*sum(b*b for b in beta)/2.
  return ll,g,info
 beta=[0.]*p;converged=False
 for iteration in range(max_iterations):
  ll,g,info=evaluate(beta);cov=invert(info);step=[sum(cov[i][j]*g[j] for j in range(p)) for i in range(p)]
  scale=1.
  for trial in range(25):
   proposal=[b+scale*d for b,d in zip(beta,step)]
   candidate=evaluate(proposal)[0]
   if candidate>=ll-1e-10:break
   scale*=.5
  beta=proposal
  if max(abs(scale*v) for v in step)<1e-7:converged=True;break
 ll,g,info=evaluate(beta);cov=invert(info)
 if not converged and max(abs(v) for v in g)>1e-4:raise RuntimeError('Cox iteration did not converge')
 result=[]
 for i,name in enumerate(names):
  se=math.sqrt(max(0,cov[i][i]));coef=beta[i]
  result.append(dict(factor=name,coef=coef,hazard_ratio=math.exp(coef),ci_low=math.exp(coef-1.96*se),ci_high=math.exp(coef+1.96*se),p_value=math.erfc(abs(coef)/se/math.sqrt(2.)) if se else None,n=len(data),events=sum(r[1] for r in data),ridge=ridge,iterations=iteration+1,reference_category=refcat,reference_district=refdist,model='Cox ridge / Breslow / first-last estimates'))
 return result

if __name__=='__main__':
 rows=[json.loads(line) for line in sys.stdin]
 for result in fit(rows):print(json.dumps(result,ensure_ascii=False))
