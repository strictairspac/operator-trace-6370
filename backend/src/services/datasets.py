from fastapi import HTTPException
from src.config.database import Session
from src.models.dataset import Dataset
from src.services.sampling import normalize_readings
from src.utils.serialization import record

def list_items():
 with Session() as s:return [record(r) for r in s.query(Dataset).order_by(Dataset.id.desc()).all()]
def get(s,item_id):
 row=s.get(Dataset,item_id)
 if not row:raise HTTPException(404,'未找到数据集')
 return row
def save(data,item_id=None):
 with Session() as s:
  row=s.get(Dataset,item_id) if item_id else Dataset()
  if not row:raise HTTPException(404,'未找到记录')
  payload=data.model_dump()
  payload['readings']=normalize_readings(payload['readings'],row.readings)
  for k,v in payload.items():setattr(row,k,v)
  row.version=(row.version or 1)+1
  s.add(row);s.commit();s.refresh(row);return record(row)
