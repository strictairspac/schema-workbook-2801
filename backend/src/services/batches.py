from datetime import datetime,timezone
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from src.models.entities import EntrySystem,Report,SwitchBatch,SwitchBatchItem,Audit
from src.utils.serialization import record
from src.services.normalization import rule_differences
MAX_ISSUES=20
def _fds(snapshot):return [(frozenset(d['lhs']),rhs) for d in snapshot['dependencies'] for rhs in d['rhs']]
def _verify(system,current,target):
    # Compare the rule projections on the system's used attributes, using the
    # dependencies frozen in each report's snapshot. Derivations may pass
    # through attributes outside the used set and still count.
    scope=list(system.attributes);issues=[]
    if not current:return [{'type':'current_missing','message':'现行报告不存在，无法核对'}]
    missing=[a for a in scope if a not in set(target.input_snapshot['relation']['attributes'])]
    if missing:issues.append({'type':'missing_attributes','attributes':missing,'message':'目标报告缺少使用属性：'+'、'.join(missing)})
    for lhs,rhs,side in rule_differences(scope,_fds(current.input_snapshot),_fds(target.input_snapshot))[:MAX_ISSUES]:
        label='、'.join(sorted(lhs)) or '∅'
        issues.append({'type':'rule_mismatch','rule':{'lhs':sorted(lhs),'rhs':rhs},'only':'current' if side=='a' else 'target','message':f"规则 {label} → {rhs} 仅{'现行' if side=='a' else '目标'}报告可推出"})
    return issues
def _shape(db,batch):
    items=list(db.scalars(select(SwitchBatchItem).where(SwitchBatchItem.batch_id==batch.id).order_by(SwitchBatchItem.id)))
    systems={s.id:s for s in db.scalars(select(EntrySystem).where(EntrySystem.id.in_([i.system_id for i in items])))} if items else {}
    out=record(batch);out['items']=[]
    for item in items:
        row=record(item);system=systems.get(item.system_id)
        row['system_code']=system.code if system else None;row['system_name']=system.name if system else None
        out['items'].append(row)
    return out
def listing(db):return [_shape(db,b) for b in db.scalars(select(SwitchBatch).order_by(SwitchBatch.id.desc()))]
def detail(db,ident):
    batch=db.get(SwitchBatch,ident)
    if not batch:raise HTTPException(404,'换版批次不存在')
    return _shape(db,batch)
def create(db,data,user):
    target=db.get(Report,data.target_report_id)
    if not target:raise HTTPException(404,'目标报告不存在')
    if target.status!='completed':raise HTTPException(422,'目标报告尚未完成，无法作为换版目标')
    systems={s.id:s for s in db.scalars(select(EntrySystem).where(EntrySystem.id.in_(data.system_ids)))}
    absent=[i for i in data.system_ids if i not in systems]
    if absent:raise HTTPException(404,'录入系统不存在：'+','.join(map(str,absent)))
    batch=SwitchBatch(name=data.name,target_report_id=target.id,status='pending');db.add(batch);db.flush()
    conflict=False
    for sid in data.system_ids:
        system=systems[sid];issues=_verify(system,db.get(Report,system.current_report_id),target)
        conflict=conflict or bool(issues)
        db.add(SwitchBatchItem(batch_id=batch.id,system_id=sid,expected_attributes=sorted(system.attributes),expected_report_id=system.current_report_id,issues=issues))
    if conflict:batch.status='conflict'
    db.add(Audit(actor=user.email,action='创建换版批次 '+data.name))
    try:db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'批次创建冲突，请调整后重试')
    return detail(db,batch.id)
def confirm(db,ident,user):
    # Lock the batch and all its systems, then re-check that nothing moved since
    # verification. Any changed scope or current report rejects the whole batch;
    # concurrent switches hit the same rule. The switch itself is one transaction,
    # so a midway failure leaves every system on its original report.
    batch=db.scalar(select(SwitchBatch).where(SwitchBatch.id==ident).with_for_update())
    if not batch:raise HTTPException(404,'换版批次不存在')
    if batch.status!='pending':raise HTTPException(409,'仅待确认批次可以确认')
    items=list(db.scalars(select(SwitchBatchItem).where(SwitchBatchItem.batch_id==batch.id).order_by(SwitchBatchItem.id)))
    systems={s.id:s for s in db.scalars(select(EntrySystem).where(EntrySystem.id.in_([i.system_id for i in items])).order_by(EntrySystem.id).with_for_update())}
    rejected=0
    for item in items:
        system=systems.get(item.system_id);problems=[]
        if not system:problems.append({'type':'system_missing','message':'确认时系统已不存在'})
        else:
            if set(system.attributes)!=set(item.expected_attributes):problems.append({'type':'scope_changed','expected':item.expected_attributes,'actual':list(system.attributes),'message':'确认时检测到使用范围已变更'})
            if system.current_report_id!=item.expected_report_id:problems.append({'type':'report_changed','expected':item.expected_report_id,'actual':system.current_report_id,'message':'确认时检测到现行报告已变更'})
        if problems:item.issues=list(item.issues or [])+problems;rejected+=1
    if rejected:
        batch.status='conflict';db.add(Audit(actor=user.email,action=f'换版批次 {batch.name} 确认被拒（{rejected} 个系统已变更）'));db.commit()
        raise HTTPException(409,'确认时有系统的使用范围或现行报告已变更，整批拒绝')
    for item in items:systems[item.system_id].current_report_id=batch.target_report_id
    batch.status='switched';batch.confirmed_at=datetime.now(timezone.utc)
    db.add(Audit(actor=user.email,action='换版批次 '+batch.name+' 已切换'))
    db.commit()
    return detail(db,batch.id)
