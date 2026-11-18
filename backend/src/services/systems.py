from sqlalchemy import select
from fastapi import HTTPException
from src.models.entities import EntrySystem,Report
from src.utils.serialization import record
from .common import save
def listing(db):return [record(x) for x in db.scalars(select(EntrySystem).order_by(EntrySystem.id))]
def _usable_report(db,ident):
    report=db.get(Report,ident)
    if not report:raise HTTPException(404,'报告不存在')
    if report.status!='completed':raise HTTPException(422,'现行报告必须是已完成报告')
    return report
def create(db,data,user):
    _usable_report(db,data.current_report_id)
    return save(db,EntrySystem(**data.model_dump()),user,'登记录入系统 '+data.code)
def update(db,ident,data,user):
    obj=db.get(EntrySystem,ident)
    if not obj:raise HTTPException(404,'录入系统不存在')
    _usable_report(db,data.current_report_id)
    for k,v in data.model_dump().items():setattr(obj,k,v)
    return save(db,obj,user,'更新录入系统 '+data.code)
