from fastapi import APIRouter,Depends
from src.config.database import db_session
from src.utils.security import current,writer
from src.schemas.batch import BatchInput
from src.services import batches as service
router=APIRouter()
@router.get('/batches')
def listing(db=Depends(db_session),user=Depends(current)):return service.listing(db)
@router.post('/batches',status_code=201)
def create(data:BatchInput,db=Depends(db_session),user=Depends(writer)):return service.create(db,data,user)
@router.get('/batches/{ident}')
def detail(ident:int,db=Depends(db_session),user=Depends(current)):return service.detail(db,ident)
@router.post('/batches/{ident}/confirm')
def confirm(ident:int,db=Depends(db_session),user=Depends(writer)):return service.confirm(db,ident,user)
