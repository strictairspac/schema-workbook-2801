from fastapi import APIRouter,Depends
from src.config.database import db_session
from src.utils.security import current,writer
from src.schemas.system import SystemInput
from src.services import systems as service
router=APIRouter()
@router.get('/systems')
def listing(db=Depends(db_session),user=Depends(current)):return service.listing(db)
@router.post('/systems',status_code=201)
def create(data:SystemInput,db=Depends(db_session),user=Depends(writer)):return service.create(db,data,user)
@router.put('/systems/{ident}')
def update(ident:int,data:SystemInput,db=Depends(db_session),user=Depends(writer)):return service.update(db,ident,data,user)
