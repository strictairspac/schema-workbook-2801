from sqlalchemy import select,func
from src.config.database import Session,Base,engine
from src.models.entities import User,Relation,Dependency,Report,EntrySystem,SwitchBatch
from src.utils.security import password_hash
from src.utils.serialization import record
from src.services.normalization import analyze

def seed():
    Base.metadata.create_all(engine)
    with Session() as db:
        for role in ('admin','operator','viewer'):
            email=role+'@nanlu.test'
            if not db.scalar(select(User).where(User.email==email)):db.add(User(email=email,password=password_hash('Demo2026!'),role=role))
        cases=[('NL-1117-A','材料检测委托单',['委托号','客户','检测项','方法','结果'],[(['委托号'],['客户']),(['检测项'],['方法']),(['委托号','检测项'],['结果'])]),('NL-1117-B','循环编号与独立属性',['A','B','C'],[(['A'],['B']),(['B'],['A'])]),('NL-1117-C','尚未确认业务依赖',['批号','容器','记录人'],[]),('NL-1117-D','材料检测委托单·修订口径',['委托号','客户','检测项','方法','结果'],[(['委托号'],['客户']),(['检测项'],['方法']),(['检测项'],['结果'])])]
        for code,title,attrs,fds in cases:
            rel=db.scalar(select(Relation).where(Relation.code==code))
            if rel:continue
            rel=Relation(code=code,title=title,attributes=attrs,note='南麓材料实验室 · 09:15 委托表复核');db.add(rel);db.flush()
            for lhs,rhs in fds:db.add(Dependency(relation_id=rel.id,lhs=lhs,rhs=rhs,note='业务确认依赖'))
        db.commit()
        rel_a=db.scalar(select(Relation).where(Relation.code=='NL-1117-A'))
        baseline=db.scalar(select(Report).where(Report.name=='baseline-20261101'))
        if rel_a and not baseline:
            deps=list(db.scalars(select(Dependency).where(Dependency.relation_id==rel_a.id)))
            snapshot={'relation':record(rel_a),'dependencies':[{'lhs':x.lhs,'rhs':x.rhs} for x in deps]}
            baseline=Report(name='baseline-20261101',relation_id=rel_a.id,status='completed',input_snapshot=snapshot,result=analyze(rel_a.attributes,snapshot['dependencies']))
            db.add(baseline);db.commit()
        if baseline:
            systems=[('LIMS-01','委托登记录入',['委托号','客户','检测项']),('LIMS-02','检测结果录入',['委托号','检测项','方法','结果']),('ARCHIVE-7','历史委托归档',['委托号','客户'])]
            for code,name,attrs in systems:
                if not db.scalar(select(EntrySystem).where(EntrySystem.code==code)):
                    db.add(EntrySystem(code=code,name=name,attributes=attrs,current_report_id=baseline.id,note='演示录入系统，共用基线报告'))
            db.commit()
        print({cls.__tablename__:db.scalar(select(func.count()).select_from(cls)) for cls in (User,Relation,Dependency,Report,EntrySystem,SwitchBatch)})
if __name__=='__main__':seed()
