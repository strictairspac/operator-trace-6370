from src.config.database import Base,engine,Session
from src.models.identity import User,Audit
from src.models.dataset import Dataset
from src.models.plan import Plan
from src.models.trace import Trace
from src.models.draft import DatasetDraft
from src.utils.security import hash_password
from src.services.operators import execute
from src.services.sampling import strip_row_id
DEFAULT_STEPS=[{'op':'scan','source':'readings'},{'op':'filter','field':'value','compare':'gte','value':50},{'op':'hash_join','right':'sensors','left_key':'sensor_id','right_key':'sensor_id'},{'op':'group','keys':['zone'],'measure':'value','aggregate':'avg'}]
def with_row_id(readings):return [{**r,'row_id':i+1} for i,r in enumerate(readings)]
def seed():
 Base.metadata.create_all(engine)
 with Session() as s:
  for role in ('admin','operator','viewer'):
   if not s.query(User).filter_by(email=role+'@operator.local').first():s.add(User(email=role+'@operator.local',role=role,password=hash_password('Trace2026!')))
  sensors=[{'sensor_id':i,'zone':['北场','南场','试验间'][i%3],'device_type':['pump','motor','valve'][i%3]} for i in range(1,13)]
  readings=[{'sensor_id':i%12+1,'value':round(25+(i*13%800)/10,1),'recorded_at':f'2026-11-17T{8+i//60:02d}:{i%60:02d}:00'} for i in range(240)]
  readings=with_row_id(readings)
  dup_reading=[{'sensor_id':1,'value':80,'recorded_at':'2026-11-17T09:00:00','row_id':1}]
  seeds=[('松原日班温升采样',sensors,readings,'240条采样 / 12个传感器 / 区域温升复核'),('空数据边界',[],[],'验证空输入和空聚合'),('重复键校验',[{'sensor_id':1,'zone':'北场','device_type':'pump'},{'sensor_id':1,'zone':'复核点','device_type':'pump'}],dup_reading,'右表重复键必须保留连接倍数')]
  for name,a,b,desc in seeds:
   if not s.query(Dataset).filter_by(name=name).first():s.add(Dataset(name=name,sensors=a,readings=b,description=desc,version=1))
  s.flush()
  for i,(name,_,_,_) in enumerate(seeds):
   pname=['过滤-连接-分组基线','空输入管线','重复键内连接'][i]
   if not s.query(Plan).filter_by(name=pname).first():s.add(Plan(name=pname,dataset_id=s.query(Dataset).filter_by(name=name).one().id,steps=DEFAULT_STEPS,note='受限DSL，Python算子真实执行'))
  demo_ds=s.query(Dataset).filter_by(name='松原日班温升采样').one()
  demo_plan=s.query(Plan).filter_by(name='过滤-连接-分组基线').one()
  if not s.query(DatasetDraft).filter_by(name='日班草稿-追加高温采样').first():
   changes={'inserts':[{'cid':'seed-cid-1','payload':{'sensor_id':3,'value':92.5,'recorded_at':'2026-11-17T10:00:00'}}],'updates':[],'deletes':[]}
   merged=[dict(r) for r in demo_ds.readings]+[{**changes['inserts'][0]['payload'],'row_id':241,'cid':'seed-cid-1'}]
   result=execute(strip_row_id({'sensors':demo_ds.sensors,'readings':merged}),demo_plan.steps)
   s.add(DatasetDraft(name='日班草稿-追加高温采样',dataset_id=demo_ds.id,changes=changes,
    base_readings=[dict(r) for r in demo_ds.readings],status='trial_completed',created_by='operator@operator.local',
    trial={'plan_id':demo_plan.id,'plan':{'id':demo_plan.id,'name':demo_plan.name,'dataset_id':demo_plan.dataset_id,'steps':demo_plan.steps,'note':demo_plan.note},
     'base_version':1,'merged_rows':len(merged),'result':result}))
  s.commit();counts={m.__tablename__:s.query(m).count() for m in (User,Dataset,Plan,Trace,DatasetDraft)};print(counts);return counts
if __name__=='__main__':seed()
