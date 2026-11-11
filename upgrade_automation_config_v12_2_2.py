from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
P=ROOT/'config'/'automation.json'
def main():
    try:
        data=json.loads(P.read_text(encoding='utf-8-sig'))
        if not isinstance(data,dict): data={}
    except Exception:
        data={}
    data.setdefault('schema_version',1)
    data.setdefault('windows_startup',{})
    ws=data['windows_startup']
    if not isinstance(ws,dict): ws={}; data['windows_startup']=ws
    ws.setdefault('enabled_by_default',True)
    ws.setdefault('start_hidden',True)
    ws.setdefault('single_instance',True)
    ws.setdefault('notify_background_alerts',True)
    P.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('automation.json V12.3 : OK')
if __name__=='__main__': main()
