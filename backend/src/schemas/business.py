from pydantic import BaseModel,Field,model_validator,ConfigDict
from typing import Literal,Optional
from src.services.operators import validate_steps
class Login(BaseModel):
 email:str;password:str
class Sensor(BaseModel):
 model_config=ConfigDict(extra='forbid')
 sensor_id:int=Field(ge=1,le=100000)
 zone:str=Field(min_length=1,max_length=40)
 device_type:Literal['pump','motor','valve']
class Reading(BaseModel):
 model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
 sensor_id:int=Field(ge=1,le=100000)
 value:float=Field(ge=-1000000,le=1000000)
 recorded_at:str=Field(min_length=1,max_length=40)
class DatasetReading(Reading):
 row_id:Optional[int]=Field(default=None,ge=1)
class DatasetInput(BaseModel):
 name:str=Field(min_length=2,max_length=120)
 description:str=Field(default='',max_length=500)
 sensors:list[Sensor]=Field(max_length=100)
 readings:list[DatasetReading]=Field(max_length=2000)
class PlanInput(BaseModel):
 name:str=Field(min_length=2,max_length=120)
 dataset_id:int
 steps:list[dict]
 note:str=Field(default='',max_length=500)
 @model_validator(mode='after')
 def validate(self):validate_steps(self.steps);return self
class TraceInput(BaseModel):
 name:str=Field(min_length=2,max_length=120)
 plan_id:int
class ChangePayload(Reading):pass
class InsertChange(BaseModel):
 model_config=ConfigDict(extra='forbid')
 cid:str=Field(min_length=1,max_length=80)
 payload:ChangePayload
class KeyedChange(BaseModel):
 model_config=ConfigDict(extra='forbid')
 row_id:int=Field(ge=1)
 payload:Optional[ChangePayload]=None
class DraftChanges(BaseModel):
 model_config=ConfigDict(extra='forbid')
 inserts:list[InsertChange]=Field(default_factory=list)
 updates:list[KeyedChange]=Field(default_factory=list)
 deletes:list[KeyedChange]=Field(default_factory=list)
class DraftInput(BaseModel):
 name:str=Field(min_length=2,max_length=120)
 dataset_id:int
 changes:DraftChanges
class DraftUpdate(BaseModel):
 name:Optional[str]=Field(default=None,min_length=2,max_length=120)
 changes:Optional[DraftChanges]=None
class TrialInput(BaseModel):
 plan_id:int
