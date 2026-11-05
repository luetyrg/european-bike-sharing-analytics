"""Apply the verified native Redash layout and readable numeric formatting."""
import json
from build_dashboard import ROOT,api,PARAMS,DEFAULTS

def main():
    m=json.loads((ROOT/'dashboard_manifest.json').read_text(encoding='utf-8'))
    titles={'kpis':'KPI города','daily':'Поездки по дням','hourly':'Почасовой спрос · на активный день',
        'heatmap':'День недели × час · поездок на наблюдаемый день',
        'station_starts':'Топ-10 станций · выдачи','station_ends':'Топ-10 станций · возвраты',
        'imbalance':'Дисбаланс станций · выдачи − возвраты','coverage':'Покрытие станционных данных'}
    for key,qid in m['queries'].items():
        api('POST',f'/api/queries/{qid}',{'name':titles[key],'description':'','query':(ROOT/'sql'/f'{key}.sql').read_text(encoding='utf-8'),'options':{'parameters':PARAMS}})
    counter_names=['Поездки','Средняя длительность','Активные станции','Поездок / активный день','Обе станции известны','Дней с поездками']
    d=api('GET',f"/api/dashboards/{m['dashboard_id']}")
    positions={0:(0,0,12,3),7:(0,11,8,7),8:(8,11,4,7),9:(0,18,12,7),
        10:(0,25,12,4),11:(0,29,6,8),12:(6,29,6,8),13:(0,37,12,9),14:(0,46,12,4),15:(0,50,12,6)}
    for w in d['widgets']:
        opts=w['options']
        pos=opts['position']
        v=w.get('visualization')
        widget_index=m['widgets'].index(w['id'])
        if widget_index in positions:
            col,row,sx,sy=positions[widget_index]
            pos.update(col=col,row=row,sizeX=sx,sizeY=sy)
        if v and v['type']=='COUNTER':
            index=counter_names.index(v['name'])
            pos.update(row=3+(index//3)*4,sizeY=4)
            if v['name']=='Обе станции известны':
                vo=v['options']; vo['stringDecimal']=2
                api('POST',f"/api/visualizations/{v['id']}",{'options':vo})
        if v and v['type']=='CHART':
            vo=v['options']
            if v['query']['id'] in [m['queries']['station_starts'],m['queries']['station_ends']]:
                vo['swappedAxes']=True
                vo.pop('invertAxes',None)
            api('POST',f"/api/visualizations/{v['id']}",{'name':'Chart','options':vo})
        elif v and v['type']=='TABLE':
            vo=v['options']
            if v['query']['id']==m['queries']['imbalance']:
                vo['columns']=[{'name':'ID','displayAs':'string'},{'name':'Выдачи','numberFormat':'0,0'},
                    {'name':'Возвраты','numberFormat':'0,0'},{'name':'Выдачи − возвраты','numberFormat':'0,0'},
                    {'name':'Дисбаланс, %','numberFormat':'0.0'}]
            else:
                vo['columns']=[{'name':'Первое наблюдение','dateTimeFormat':'DD.MM.YYYY'},
                    {'name':'Последнее наблюдение','dateTimeFormat':'DD.MM.YYYY'}]
            api('POST',f"/api/visualizations/{v['id']}",{'name':'Table','options':vo})
        api('POST',f"/api/widgets/{w['id']}",{'options':opts,'text':w['text']})
    d=api('GET',f"/api/dashboards/{m['dashboard_id']}")
    api('POST',f"/api/dashboards/{m['dashboard_id']}",{'version':d['version'],'options':{'parameterValues':DEFAULTS,'parameters':PARAMS}})
    print('Readable layout and single-city filter applied.')

if __name__=='__main__': main()
