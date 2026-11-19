from sqlalchemy import Column,Integer,String,JSON,DateTime,ForeignKey,func
from src.config.database import Base
class DatasetDraft(Base):
 __tablename__='dataset_drafts'
 id=Column(Integer,primary_key=True)
 name=Column(String(120),nullable=False)
 dataset_id=Column(Integer,ForeignKey('datasets.id'),nullable=False)
 changes=Column(JSON,nullable=False)
 base_readings=Column(JSON,nullable=False)
 status=Column(String(20),default='open',nullable=False)
 trial=Column(JSON,nullable=True)
 publish=Column(JSON,nullable=True)
 created_by=Column(String(120),nullable=False)
 created_at=Column(DateTime,server_default=func.now())
 updated_at=Column(DateTime,server_default=func.now(),onupdate=func.now())
