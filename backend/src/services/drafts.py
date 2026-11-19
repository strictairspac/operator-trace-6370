"""Sampling drafts: staged row changes, trial runs and guarded batch publish."""
from fastapi import HTTPException
from src.config.database import Session
from src.models.dataset import Dataset
from src.models.plan import Plan
from src.models.draft import DatasetDraft
from src.services.operators import execute
from src.services.sampling import (apply_changes,detect_conflicts,draft_view,
 normalize_readings,strip_row_id,validate_changes)
from src.utils.serialization import record

def _dump(changes):
 return changes.model_dump() if hasattr(changes,'model_dump') else changes

def _preview(dataset,changes):
 merged=apply_changes(dataset['readings'],_dump(changes))
 return {'merged_readings':draft_view(merged),'merged_rows':len(merged)}

def list_items(dataset_id=None):
 with Session() as s:
  q=s.query(DatasetDraft)
  if dataset_id is not None:q=q.filter(DatasetDraft.dataset_id==dataset_id)
  return [record(r) for r in q.order_by(DatasetDraft.id.desc()).all()]

def detail(item_id):
 with Session() as s:
  row=s.get(DatasetDraft,item_id)
  if not row:raise HTTPException(404,'未找到采样草稿')
  d=s.get(Dataset,row.dataset_id)
  out=record(row)
  out['preview']=_preview(record(d),row.changes) if row.status!='published' else None
  out['dataset']=record(d)
  return out

def create(data,user):
 changes=validate_changes(_dump(data.changes))
 with Session() as s:
  d=s.get(Dataset,data.dataset_id)
  if not d:raise HTTPException(404,'未找到数据集')
  # Self-heal rows predating the row_id schema without bumping the content version.
  if any(not isinstance(r,dict) or 'row_id' not in r for r in d.readings):
   d.readings=normalize_readings(d.readings)
  current=record(d)
  # Fail fast if any keyed change references a row that is already missing.
  apply_changes(current['readings'],changes)
  row=DatasetDraft(name=data.name,dataset_id=d.id,changes=changes,
   base_readings=current['readings'],status='open',created_by=user.email)
  s.add(row);s.commit();s.refresh(row);return detail(row.id)

def update(item_id,data,user):
 with Session() as s:
  row=s.get(DatasetDraft,item_id)
  if not row:raise HTTPException(404,'未找到采样草稿')
  if row.status=='published':raise HTTPException(400,'草稿已发布，不能再修改')
  d=s.get(Dataset,row.dataset_id)
  if data.name is not None:row.name=data.name
  if data.changes is not None:
   changes=validate_changes(_dump(data.changes))
   apply_changes(record(d)['readings'],changes)
   row.changes=changes
  # Editing a draft invalidates any earlier trial result.
  row.trial=None;row.status='open';row.publish=None
  s.commit();s.refresh(row);return detail(row.id)

def trial(item_id,data,user):
 with Session() as s:
  row=s.get(DatasetDraft,item_id)
  if not row:raise HTTPException(404,'未找到采样草稿')
  if row.status=='published':raise HTTPException(400,'草稿已发布，无需试跑')
  d=s.get(Dataset,row.dataset_id)
  plan=s.get(Plan,data.plan_id)
  if not plan:raise HTTPException(404,'未找到算子计划')
  if plan.dataset_id!=d.id:raise HTTPException(400,'计划不属于该数据集，请选择本数据集的计划')
  ds=record(d)
  merged=apply_changes(ds['readings'],row.changes)
  trial_ds={'sensors':ds['sensors'],'readings':merged}
  result=execute(strip_row_id(trial_ds),plan.steps)
  row.trial={'plan_id':plan.id,'plan':record(plan),'base_version':ds['version'],
   'merged_rows':len(merged),'result':result}
  row.status='trial_completed';row.publish=None
  s.commit();s.refresh(row);return detail(row.id)

def publish(item_id,user):
 with Session() as s:
  # Row lock serializes publishes against concurrent full-dataset saves.
  row=s.query(DatasetDraft).filter(DatasetDraft.id==item_id).with_for_update().first()
  if not row:raise HTTPException(404,'未找到采样草稿')
  if row.status=='published':return detail(item_id)
  if not row.trial:raise HTTPException(400,'请先选择一份计划试跑，通过后再发布')
  d=s.query(Dataset).filter(Dataset.id==row.dataset_id).with_for_update().first()
  ds=record(d)
  # 1) Same-row conflict: others touched a row this draft also edits.
  conflicts=detect_conflicts(ds['readings'],row.base_readings,row.changes)
  if conflicts:
   reason={'reason':'row_conflict','message':'撞改同一行：其他助教在试跑后修改或删除了这些采样，正式数据保持不变','conflicts':conflicts}
   row.publish=reason;row.status='open';s.commit()
   raise HTTPException(409,reason)
  # 2) Replay: merge onto the latest live rows, keeping everyone else's edits.
  merged=apply_changes(ds['readings'],row.changes)
  plan=row.trial['plan']
  replay_ds={'sensors':ds['sensors'],'readings':merged}
  replay=execute(strip_row_id(replay_ds),plan['steps'])
  if replay['checksum']!=row.trial['result']['checksum'] or replay['output_rows']!=row.trial['result']['output_rows']:
   reason={'reason':'result_drift','message':'合并他人修改后，用试跑时的计划算不出与试跑相同的结果，正式数据保持不变',
    'trial_checksum':row.trial['result']['checksum'],'replay_checksum':replay['checksum'],
    'trial_output_rows':row.trial['result']['output_rows'],'replay_output_rows':replay['output_rows'],
    'live_version':ds['version'],'trial_base_version':row.trial['base_version']}
   row.publish=reason;row.status='open';s.commit()
   raise HTTPException(409,reason)
  # 3) All clear: one atomic swap, so profiles read only the full old or new version.
  # cid is an append-dedup token scoped to the draft; it must not enter official data.
  d.readings=[{k:v for k,v in r.items() if k!='cid'} for r in merged];d.version=ds['version']+1
  row.status='published'
  row.publish={'reason':'ok','message':'整批发布成功',
   'from_version':ds['version'],'to_version':d.version,
   'published_rows':len(merged),'plan_id':plan['id'],'checksum':replay['checksum']}
  s.commit();s.refresh(row);return detail(item_id)
