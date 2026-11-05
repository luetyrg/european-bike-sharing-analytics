"""Create native Redash queries, visualizations and widgets through the local API."""
import json
import time
import urllib.request
import urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:5001'
CREDENTIALS=json.loads((ROOT/'private/credentials.json').read_text(encoding='utf-8'))
PARAMS=[
 {'name':'city','title':'Город','type':'enum','value':'Bilbao','enumOptions':'Bilbao\nBerlin\nDresden\nWarszawa'},
 {'name':'period','title':'Период начала поездки','type':'date-range','value':{'start':'2022-08-26','end':'2023-07-15'}}
]
DEFAULTS={p['name']:p['value'] for p in PARAMS}

def api(method,path,data=None):
    req=urllib.request.Request(BASE+path, data=json.dumps(data).encode() if data is not None else None,
        headers={'Authorization':'Key '+CREDENTIALS['api_key'],'Content-Type':'application/json'},method=method)
    try:
        with urllib.request.urlopen(req,timeout=60) as r: return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'{method} {path}: {e.code}: {e.read().decode()[:1600]}') from None

def run(qid,params=None):
    result=api('POST',f'/api/queries/{qid}/results',{'parameters':params or DEFAULTS,'max_age':0})
    deadline=time.monotonic()+90
    while 'job' in result:
        job=result['job']
        if job['status']==3: return api('GET',f"/api/query_results/{job['query_result_id']}")['query_result']
        if job['status'] in (4,5): raise RuntimeError(str(job))
        if time.monotonic()>deadline: raise TimeoutError(f'Query {qid}')
        time.sleep(.5)
        result=api('GET',f"/api/jobs/{job['id']}")
    return result['query_result']

def chart(x,y,kind='column',color='#2563eb',**extra):
    opts={'globalSeriesType':kind,'columnMapping':{x:'x',y:'y'},'legend':{'enabled':False},
        'xAxis':{'type':'category' if kind=='column' else '-','labels':{'enabled':True},'title':{'text':''}},
        'yAxis':[{'type':'linear','title':{'text':''}}],
        'seriesOptions':{y:{'color':color,'name':'Поездки'}},'sortX':False,'showDataLabels':False,
        'missingValuesAsZero':False,'numberFormat':'0,0[.]0'}
    opts.update(extra)
    return opts

def build():
    state_file=ROOT/'dashboard_manifest.json'
    if state_file.exists():
        print('Dashboard already exists; use validate_dashboard.py to verify it.')
        return
    sources=api('GET','/api/data_sources')
    ds=next((s for s in sources if s['name']=='Bike Sharing · PostgreSQL'),None)
    if not ds:
        ds=api('POST','/api/data_sources',{'name':'Bike Sharing · PostgreSQL','type':'pg','options':{
            'host':'postgres','port':5432,'dbname':'redash','user':'bike_reader','password':CREDENTIALS['reader_password'],'sslmode':'prefer'}})
    dashboard=api('POST','/api/dashboards',{'name':'Велопрокат · спрос и станции'})
    manifest={'dashboard_id':dashboard['id'],'url':BASE+'/dashboards/'+str(dashboard['id']),'queries':{},'visualizations':{},'widgets':[]}
    def widget(vis_id,col,row,w,h,text_value='',title=None):
        options={'position':{'col':col,'row':row,'sizeX':w,'sizeY':h,'autoHeight':False},
            'parameterMappings':{p['name']:{'name':p['name'],'type':'dashboard-level','mapTo':p['name'],'value':None,'title':p['title']} for p in PARAMS}}
        if title: options['title']=title
        result=api('POST','/api/widgets',{'dashboard_id':dashboard['id'],'visualization_id':vis_id,'text':text_value,'width':1,'options':options})
        manifest['widgets'].append(result['id'])
        return result
    widget(None,0,0,12,3,text_value='## Спрос, пиковые часы и баланс станций\nИсторические поездки **26.08.2022–15.07.2023** · Berlin, Warszawa, Dresden, Bilbao. Выберите город и период, затем нажмите **Apply Changes**. Все панели используют общие фильтры. Время — местное для города.\n\n**Цель:** найти пики спроса и станции с наибольшим расхождением выдач и возвратов. Это анализ поездок, а не мониторинг наличия велосипедов.')
    specs=[('kpis','01 · KPI выбранного города'),('daily','02 · Динамика поездок'),('hourly','03 · Почасовой профиль'),('heatmap','04 · День недели × час'),('station_starts','05 · Топ станций выдачи'),('station_ends','06 · Топ станций возврата'),('imbalance','07 · Дисбаланс станций'),('coverage','08 · Полнота станционных данных')]
    queries={}
    for filename,title in specs:
        q=api('POST','/api/queries',{'name':title,'data_source_id':ds['id'],'query':(ROOT/'sql'/f'{filename}.sql').read_text(encoding='utf-8'),
            'description':'',
            'options':{'parameters':PARAMS},'is_draft':False,'tags':['bike-sharing','portfolio','BI']})
        queries[filename]=q
        manifest['queries'][filename]=q['id']
        res=run(q['id'])
        print(filename,'rows',len(res['data']['rows']),flush=True)
    def vis(key,name,typ,options):
        q=queries[key]
        v=api('POST','/api/visualizations',{'query_id':q['id'],'type':typ,'name':name,'description':'','options':options})
        manifest['visualizations'][name]=v['id']
        return v['id']
    counters=[('trips','Поездки',0,''),('mean_duration_min','Средняя длительность',1,' мин'),('active_stations','Активные станции',0,''),
              ('trips_per_active_day','Поездок / активный день',1,''),('station_pair_pct','Обе станции известны',2,' %'),('active_days','Дней с поездками',0,'')]
    for i,(col,label,dec,suffix) in enumerate(counters):
        v=vis('kpis',label,'COUNTER',{'counterColName':col,'counterLabel':label,'rowNumber':1,'stringDecimal':dec,'stringDecChar':',','stringThouSep':' ','stringSuffix':suffix})
        widget(v,(i%3)*4,3+(i//3)*3,4,3)
    v=vis('daily','Поездки по дням','CHART',chart('date','trips','line',xAxis={'type':'datetime','title':{'text':'Дата начала поездки'}}))
    widget(v,0,9,8,7)
    v=vis('hourly','Спрос по часам · на активный день','CHART',chart('hour','trips_per_active_day',color='#0d9488',xAxis={'type':'linear','title':{'text':'Час начала поездки · местное время'}}))
    widget(v,8,9,4,7)
    opts=chart('hour','weekday','heatmap',columnMapping={'hour':'x','weekday':'y','trips_per_observed_day':'zVal'},colorScheme='Viridis',
        xAxis={'type':'category','title':{'text':'Час начала поездки'}},yAxis=[{'type':'category','title':{'text':'День недели'}}])
    v=vis('heatmap','Пиковые часы · поездок на наблюдаемый день недели','CHART',opts)
    widget(v,0,16,12,7)
    widget(None,0,23,12,4,text_value='### Станции: активность и дисбаланс\nНиже учитываются только известные station IDs. Проверяйте полноту данных в таблице внизу: Berlin и особенно Dresden имеют много поездок без связи со станцией. **Активная станция** встречается хотя бы в одной выдаче или возврате в выбранной когорте поездок.\n\nВыдачи и возвраты относятся к поездкам, **начавшимся** в выбранный период. Положительный баланс «выдачи − возвраты» означает наблюдаемый отток; отрицательный — приток. Это не остаток велосипедов на станции.')
    for key,value,title,col,color in [('station_starts','starts','Топ-10 станций · выдачи',0,'#2563eb'),('station_ends','ends','Топ-10 станций · возвраты',6,'#0d9488')]:
        v=vis(key,title,'CHART',chart('station',value,color=color,swappedAxes=True))
        widget(v,col,27,6,8)
    for key,title,row,height in [('imbalance','Наибольший дисбаланс · выбранная когорта поездок',35,9),('coverage','Полнота данных · выбранный город и период',44,4)]:
        v=vis(key,title,'TABLE',{'itemsPerPage':15,'columns':[]})
        widget(v,0,row,12,height)
    widget(None,0,48,12,6,text_value='### Как читать показатели\n**Поездок / активный день** = число поездок / число дат с наблюдаемыми поездками. Отсутствие поездок в исходнике не доказывает нулевой спрос: на дневном графике такие даты оставлены пустыми. Тепловая карта делит число поездок на количество наблюдаемых дат соответствующего дня недели.\n\n**Средняя длительность** рассчитана по валидным длительностям 1–360 минут, с взвешиванием по числу поездок; исключённые длительности не исключают сами поездки из спроса. Station IDs Варшавы объединены из двух записей города.\n\nИсточник: [TUM European Bike Sharing Dataset](https://github.com/TUMFTM/european-bike-sharing-dataset), [исследование в Transportation](https://doi.org/10.1007/s11116-025-10661-2), CC BY-NC 4.0. Данные исторические; проект не устанавливает причины различий и не оценивает фактическую доступность парка.')
    current=api('GET',f"/api/dashboards/{dashboard['id']}")
    api('POST',f"/api/dashboards/{dashboard['id']}",{'is_draft':False,'tags':['bike-sharing','portfolio','BI'],'version':current['version'],'options':{'parameterValues':DEFAULTS,'parameters':PARAMS}})
    state_file.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Dashboard ready:',manifest['url'])

if __name__=='__main__': build()
