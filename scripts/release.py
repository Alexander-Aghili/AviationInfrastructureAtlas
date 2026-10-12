"""FAA NASR 28-day cycle arithmetic and the cycle retained in data/raw."""
import datetime,json,pathlib
ANCHOR=datetime.date(2026,10,1)  # A published NASR effective date; cycles repeat every 28 days.
BASE='https://nfdc.faa.gov/webContent/28DaySub/'
MONTHS=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
def cycle_on(day):
    """Latest cycle effective on or before day, as YYYY-MM-DD."""
    return (ANCHOR+datetime.timedelta(days=(day-ANCHOR).days//28*28)).isoformat()
def next_cycle(cycle):return (datetime.date.fromisoformat(cycle)+datetime.timedelta(days=28)).isoformat()
def is_cycle(cycle):return (datetime.date.fromisoformat(cycle)-ANCHOR).days%28==0
def prefix(cycle):
    """FAA CSV archive prefix, e.g. 2026-10-01 -> 01_Oct_2026 (locale-independent)."""
    d=datetime.date.fromisoformat(cycle);return f'{d.day:02d}_{MONTHS[d.month-1]}_{d.year}'
def csv_dir(raw,cycle,group):return pathlib.Path(raw)/f'{prefix(cycle)}_{group}_CSV'
def csv_url(cycle,group):return BASE+f'extra/{prefix(cycle)}_{group}_CSV.zip'
def subscription_url(cycle):return f'https://www.faa.gov/air_traffic/flight_info/aeronav/aero_data/NASR_Subscription/{cycle}/'
def retained_cycle(raw):
    """The single NASR cycle whose files are retained in raw/manifest.json."""
    cycles={e.get('cycle') or next((c for c in [cycle_from_url(e['url'])] if c),None) for e in json.loads((pathlib.Path(raw)/'manifest.json').read_text())}-{None}
    if len(cycles)!=1:raise ValueError('Retained FAA files must come from exactly one NASR cycle: '+', '.join(sorted(cycles)))
    return cycles.pop()
def cycle_from_url(url):
    name=url.rsplit('/',1)[-1]
    for part in [name[:11],url.rsplit('/',2)[-2] if url.count('/')>1 else '']:
        try:
            if len(part)==10:return datetime.date.fromisoformat(part).isoformat()
            day,month,year=part.split('_');return datetime.date(int(year),MONTHS.index(month)+1,int(day)).isoformat()
        except ValueError:continue
    return None
