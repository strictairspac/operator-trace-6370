from fastapi import APIRouter,Depends
from src.middlewares.auth import current,writer
from src.schemas.business import DraftInput,DraftUpdate,TrialInput
from src.services import drafts
from src.services.audit import log
router=APIRouter()
@router.get('/drafts')
def listing(dataset_id:int=None,u=Depends(current)):return drafts.list_items(dataset_id)
@router.get('/drafts/{item_id}')
def detail(item_id:int,u=Depends(current)):return drafts.detail(item_id)
@router.post('/drafts')
def create(data:DraftInput,u=Depends(writer)):
 row=drafts.create(data,u);log(u.email,'draft.create',row['name']);return row
@router.put('/drafts/{item_id}')
def update(item_id:int,data:DraftUpdate,u=Depends(writer)):
 row=drafts.update(item_id,data,u);log(u.email,'draft.update',row['name']);return row
@router.post('/drafts/{item_id}/trial')
def trial(item_id:int,data:TrialInput,u=Depends(writer)):
 row=drafts.trial(item_id,data,u);log(u.email,'draft.trial',row['name']);return row
@router.post('/drafts/{item_id}/publish')
def publish(item_id:int,u=Depends(writer)):
 row=drafts.publish(item_id,u);log(u.email,'draft.publish',row['name']);return row
