"""Streaming mapper executed on YTsaurus Linux workers (stdlib only)."""
import json,sys,re
from datetime import datetime,timezone,timedelta
from collections import defaultdict
rules=json.load(open('topic_rules.json',encoding='utf8'))
cutoff=datetime.fromisoformat(sys.argv[1]).date()
counts=defaultdict(lambda:[0]*14)
diag=defaultdict(int)
examples={}
for line in sys.stdin:
    r=json.loads(line)
    diag["rows"]+=1
    if not r.get('branch_id') or not r.get('review_id'):
        diag['missing_ids']+=1;continue
    rating=r.get('rating')
    if r.get('is_hidden') is not False or not isinstance(rating,int) or not 1<=rating<=5:
        diag['hidden_or_rating']+=1;examples['rating_type']=str(type(rating));continue
    try:
        stamp=r['date_created'].replace('Z','+00:00')
        # Python <3.11 accepts only 3/6 fractional digits; 2GIS uses 1..6.
        stamp=re.sub(r'\.(\d+)(?=[+-]|$)',lambda m:'.'+m.group(1).ljust(6,'0')[:6],stamp)
        dt=datetime.fromisoformat(stamp)
        if dt.tzinfo:dt=dt.astimezone(timezone(timedelta(hours=3)))
        if dt.date()>cutoff:
            diag['after_cutoff']+=1;continue
    except (ValueError,TypeError,KeyError,AttributeError):
        diag['invalid_date']+=1;examples['date']=r.get('date_created');continue
    diag['eligible']+=1
    a=counts[str(r['branch_id'])];a[0]+=1;a[8+rating]+=1
    if rating<=2:
        a[1]+=1
        text=(r.get('text') or '').lower()
        a[2]+=int(bool(text.strip()))
        matched=[any(k in text for k in terms) for terms in rules.values()]
        for i,m in enumerate(matched):a[3+i]+=int(m)
        a[8]+=int(not any(matched))
for branch,a in counts.items():
    print(json.dumps(dict(branch_id=branch,**{'c'+str(i):v for i,v in enumerate(a)}),ensure_ascii=False))

print(json.dumps({"diagnostics":dict(diag),"examples":examples}),file=sys.stderr)
