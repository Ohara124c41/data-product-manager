import json, os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import numpy as np

os.makedirs('outputs/flyber/charts',exist_ok=True)
d=json.load(open('flyber_analysis.json'))['section5']
dates=[datetime.fromisoformat(x['date']) for x in d]
colors={'Choose Car':'#2F75B5','Search':'#70AD47','Open':'#5B9BD5','Begin Ride':'#ED7D31','Request Car':'#A5A5A5','Total Event':'#17365D'}

def base(title,ylabel):
    fig,ax=plt.subplots(figsize=(10,4.8),dpi=180)
    ax.set_title(title,loc='left',fontsize=15,fontweight='bold',color='#17365D')
    ax.set_ylabel(ylabel); ax.grid(axis='y',alpha=.22); ax.spines[['top','right']].set_visible(False)
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1)); ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    return fig,ax
def save(fig,name): fig.tight_layout(); fig.savefig(f'outputs/flyber/charts/{name}.png',bbox_inches='tight',facecolor='white'); plt.close(fig)

for key,name,title in [('Choose Car','choose_car_trend','Choose Car events grew sharply during the month'),('Begin Ride','begin_ride_trend','Begin Ride events increased, then normalized after the campaign peak')]:
    fig,ax=base(title,'Daily events')
    y=[x[key] for x in d]; ax.plot(dates,y,lw=2.7,color=colors[key]); ax.fill_between(dates,y,alpha=.12,color=colors[key])
    ax.axvspan(datetime(2019,10,1),datetime(2019,10,7),color='#FFC000',alpha=.15,label='Marketing campaign: Oct 1-7')
    ax.legend(frameon=False,loc='upper left'); ax.ticklabel_format(style='plain',axis='y'); save(fig,name)

fig,ax=base('Daily event logs increased 16.18x over one month','Total daily events')
y=[x['Total Event'] for x in d]; ax.plot(dates,y,lw=3,color=colors['Total Event']); ax.fill_between(dates,y,alpha=.12,color=colors['Total Event'])
ax.scatter([dates[0],dates[-1]],[y[0],y[-1]],color=colors['Total Event'],zorder=5)
ax.annotate(f'{y[0]:,.0f}',(dates[0],y[0]),xytext=(7,8),textcoords='offset points'); ax.annotate(f'{y[-1]:,.0f}',(dates[-1],y[-1]),xytext=(-55,8),textcoords='offset points')
ax.axvspan(datetime(2019,10,1),datetime(2019,10,7),color='#FFC000',alpha=.15,label='Marketing campaign: Oct 1-7'); ax.legend(frameon=False,loc='upper left'); ax.ticklabel_format(style='plain',axis='y'); save(fig,'total_event_growth')

fig,ax=base('All event types follow the same campaign-driven pattern','Daily events (log scale)')
for key in ['Choose Car','Search','Open','Begin Ride','Request Car']:
    ax.plot(dates,[x[key] for x in d],lw=2,label=key,color=colors[key])
ax.set_yscale('log'); ax.axvspan(datetime(2019,10,1),datetime(2019,10,7),color='#FFC000',alpha=.15)
ax.legend(ncol=3,frameon=False,loc='upper left'); save(fig,'all_event_types_log')

def mean(key,lo,hi): return np.mean([x[key] for x in d if lo<=x['date']<=hi])
metrics={
 'growth_multiple':d[-1]['Total Event']/d[0]['Total Event'],
 'absolute_growth':d[-1]['Total Event']-d[0]['Total Event'],
 'growth_percent':(d[-1]['Total Event']/d[0]['Total Event']-1)*100,
 'peak_date':max(d,key=lambda x:x['Total Event'])['date'],
 'peak_total':max(x['Total Event'] for x in d),
 'event_growth':{k:d[-1][k]/d[0][k] for k in ['Choose Car','Search','Open','Begin Ride','Request Car']},
 'pre_campaign_avg':mean('Total Event','2019-09-24','2019-09-30'),
 'campaign_avg':mean('Total Event','2019-10-01','2019-10-07'),
 'post_campaign_avg':mean('Total Event','2019-10-08','2019-10-11'),
}
metrics['campaign_vs_pre_pct']=(metrics['campaign_avg']/metrics['pre_campaign_avg']-1)*100
json.dump(metrics,open('flyber_metrics.json','w'),indent=2)
print(json.dumps(metrics,indent=2))
