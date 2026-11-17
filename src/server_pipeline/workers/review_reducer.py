"""Sum mapper counters by branch_id on YTsaurus workers."""
import sys,json
last=None;counts=None
for line in sys.stdin:
    row=json.loads(line);key=row['branch_id']
    if key!=last:
        if counts is not None:print(json.dumps(dict(branch_id=last,**counts)))
        last=key;counts={'c'+str(i):0 for i in range(14)}
    for k in counts:counts[k]+=row[k]
if counts is not None:print(json.dumps(dict(branch_id=last,**counts)))
