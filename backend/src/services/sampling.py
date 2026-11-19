"""Sampling-draft row identity, change merge and conflict detection.

Readings carry a stable ``row_id`` so equal-value samples can be edited
independently. Operators must never see row_id, so the execution view strips
it; stored rows and trace snapshots keep it.
"""
from fastapi import HTTPException

READING_KEYS={'sensor_id','value','recorded_at'}
MAX_READINGS=2000

def normalize_readings(readings,existing=None):
 """Assign stable row_id values to a full readings replacement.

 Provided row_ids survive round trips; new rows receive ids above the current
 maximum so identities never collide within a dataset.
 """
 if not isinstance(readings,list):raise HTTPException(400,'readings 必须是数组')
 used=set()
 out=[]
 max_id=0
 for r in existing or []:
  if isinstance(r,dict) and isinstance(r.get('row_id'),int):max_id=max(max_id,r['row_id'])
 for r in readings:
  if not isinstance(r,dict):raise HTTPException(400,'采样行必须是对象')
  rid=r.get('row_id')
  if rid is None:
   max_id+=1;rid=max_id
  elif not isinstance(rid,int) or isinstance(rid,bool) or rid<1:
   raise HTTPException(400,'row_id 必须是正整数')
  if rid in used:raise HTTPException(400,'row_id 重复：%s'%rid)
  used.add(rid)
  out.append({**{k:r[k] for k in READING_KEYS},'row_id':rid})
 if len(out)>MAX_READINGS:raise HTTPException(400,'采样最多 2000 行')
 return out

INTERNAL_KEYS={'row_id','cid'}
def strip_row_id(dataset):
 """Return a dataset view without draft-internal keys, suitable for the Python engine."""
 return {'sensors':dataset['sensors'],'readings':[{k:v for k,v in r.items() if k not in INTERNAL_KEYS} for r in dataset['readings']]}

def empty_changes():return {'inserts':[],'updates':[],'deletes':[]}

def validate_changes(changes,max_rows=MAX_READINGS):
 if not isinstance(changes,dict):raise HTTPException(400,'changes 必须是对象')
 for key in ('inserts','updates','deletes'):
  if key not in changes or not isinstance(changes[key],list):raise HTTPException(400,'changes.%s 必须是数组'%key)
 if set(changes)!= {'inserts','updates','deletes'}:raise HTTPException(400,'changes 仅允许 inserts/updates/deletes')
 total=sum(len(changes[k]) for k in changes)
 if total==0:raise HTTPException(400,'草稿至少包含一条增删改')
 if total>max_rows:raise HTTPException(400,'草稿变更最多 %s 条'%max_rows)
 for ch in changes['inserts']+changes['updates']:
  if not isinstance(ch,dict):raise HTTPException(400,'变更项必须是对象')
  if set(ch.get('payload',{}))!=READING_KEYS:raise HTTPException(400,'变更负载只允许 sensor_id/value/recorded_at')
 for ch in changes['inserts']:
  if not isinstance(ch.get('cid'),str) or not 1<=len(ch['cid'])<=80:raise HTTPException(400,'插入项需要客户端 cid')
 for ch in changes['updates']+changes['deletes']:
  if not isinstance(ch.get('row_id'),int) or isinstance(ch['row_id'],bool) or ch['row_id']<1:
   raise HTTPException(400,'更新/删除项需要 row_id')
 cids=[c['cid'] for c in changes['inserts']]
 if len(set(cids))!=len(cids):raise HTTPException(400,'cid 重复，无法保证重试不重复追加')
 return changes

def apply_changes(readings,changes):
 """Apply draft changes onto a readings list; returns a new list.

 Never mutates the input: baseline snapshots must stay intact for conflict
 detection across retries.
 """
 ids={r['row_id'] for r in readings}
 for ch in changes['updates']+changes['deletes']:
  if ch['row_id'] not in ids:raise HTTPException(400,'row_id %s 已不存在，无法应用草稿'%ch['row_id'])
 updates={c['row_id']:c['payload'] for c in changes['updates'] if c.get('payload')}
 delete_ids={c['row_id'] for c in changes['deletes']}
 out=[{**r,**updates[r['row_id']]} if r['row_id'] in updates else dict(r)
      for r in readings if r['row_id'] not in delete_ids]
 max_id=max(ids,default=0)
 for ch in changes['inserts']:
  max_id+=1
  out.append({**ch['payload'],'row_id':max_id,'cid':ch['cid']})
 if len(out)>MAX_READINGS:raise HTTPException(400,'合并后采样超过 2000 行，请减少变更')
 return out

def detect_conflicts(live_readings,base_readings,changes):
 """Return rows changed by others between draft baseline and publish time."""
 live={r['row_id']:r for r in live_readings}
 base={r['row_id']:r for r in base_readings}
 touched={c['row_id'] for c in changes['updates']}|{c['row_id'] for c in changes['deletes']}
 conflicts=[]
 for rid in sorted(touched):
  b=base.get(rid);l=live.get(rid)
  if b is None:continue
  if l is None:
   conflicts.append({'row_id':rid,'kind':'deleted_by_other','base':b})
  elif {k:l.get(k) for k in READING_KEYS}!={k:b.get(k) for k in READING_KEYS}:
   conflicts.append({'row_id':rid,'kind':'updated_by_other','base':b,'live':l})
 return conflicts

def draft_view(readings):return [{k:v for k,v in r.items()} for r in readings]
