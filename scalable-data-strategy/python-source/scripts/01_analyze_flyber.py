from zipfile import ZipFile
from xml.etree import ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import json, math, statistics

NS='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'

def shared_strings(z):
    out=[]
    for ev,e in ET.iterparse(z.open('xl/sharedStrings.xml'),events=('end',)):
        if e.tag==NS+'si':
            out.append(''.join(t.text or '' for t in e.iter() if t.tag==NS+'t')); e.clear()
    return out

def excel_date(v):
    return (datetime(1899,12,30)+timedelta(days=float(v))).date().isoformat()

def event_log(path):
    with ZipFile(path) as z:
        ss=shared_strings(z)
        total=Counter(); by_event=Counter(); by_device=Counter(); by_page=Counter(); by_location=Counter()
        row_count=0; users=defaultdict(set); sessions=defaultdict(set)
        for ev,e in ET.iterparse(z.open('xl/worksheets/sheet1.xml'),events=('end',)):
            if e.tag!=NS+'row': continue
            row={}
            for c in e.findall(NS+'c'):
                ref=c.attrib.get('r',''); col=''.join(x for x in ref if x.isalpha())
                v=c.find(NS+'v'); val='' if v is None else v.text
                if c.attrib.get('t')=='s' and val: val=ss[int(val)]
                row[col]=val
            if row_count>0 and row.get('D'):
                d=excel_date(row['D']); total[d]+=1
                by_event[d,row.get('I','')]+=1; by_device[d,row.get('E','')]+=1
                by_page[d,row.get('H','')]+=1; by_location[d,row.get('G','')]+=1
                users[d].add(row.get('C','')); sessions[d].add(row.get('F',''))
            row_count+=1; e.clear()
    def matrix(counter, cats):
        dates=sorted(total)
        return {'dates':dates,'categories':cats,'values':[[counter[d,c] for d in dates] for c in cats]}
    return {
      'dates':sorted(total),'total':[total[d] for d in sorted(total)],
      'events':matrix(by_event,['choose_car','search','open','begin_ride','request_car']),
      'devices':matrix(by_device,['ios','android','desktop_web','mobile_web']),
      'pages':matrix(by_page,['search_page','book_page','driver_page','splash_page']),
      'locations':matrix(by_location,['Manhattan','Brooklyn','Bronx','Queens','Staten Island']),
      'unique_users':[len(users[d]) for d in sorted(total)],'unique_sessions':[len(sessions[d]) for d in sorted(total)],
      'raw_rows':row_count-1,
    }

def section5(path):
    with ZipFile(path) as z:
        ss=shared_strings(z)
        rows=[]
        for ev,e in ET.iterparse(z.open('xl/worksheets/sheet1.xml'),events=('end',)):
            if e.tag!=NS+'row': continue
            row={}
            for c in e.findall(NS+'c'):
                ref=c.attrib.get('r',''); col=''.join(x for x in ref if x.isalpha())
                v=c.find(NS+'v'); val='' if v is None else v.text
                if c.attrib.get('t')=='s' and val: val=ss[int(val)]
                row[col]=val
            rows.append(row); e.clear()
    headers=[rows[0].get(c,'') for c in 'ABCDEFG']
    data=[]
    for r in rows[1:]:
        if r.get('A'):
            data.append({'date':excel_date(r['A']),**{headers[i]:float(r.get(chr(65+i),'0')) for i in range(1,7)}})
    return data

etl=event_log('upload/section-3-event-logs-template.xlsx')
s5=section5('upload/section-5-data.xlsx')
out={'etl':etl,'section5':s5}
with open('flyber_analysis.json','w') as f: json.dump(out,f,indent=2)
print(json.dumps(etl,indent=2))
print('SECTION5 rows',len(s5),'first',s5[0],'last',s5[-1])
for k in ['Choose Car','Search','Open','Begin Ride','Request Car','Total Event']:
    print(k,'first',s5[0][k],'last',s5[-1][k],'ratio',s5[-1][k]/s5[0][k], 'peak',max(x[k] for x in s5))
