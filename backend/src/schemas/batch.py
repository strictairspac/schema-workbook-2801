from pydantic import BaseModel,Field,field_validator
class BatchInput(BaseModel):
    name:str=Field(min_length=2,max_length=120)
    target_report_id:int=Field(gt=0)
    system_ids:list[int]=Field(min_length=1,max_length=50)
    @field_validator('system_ids')
    @classmethod
    def ids_valid(cls,value):
        if len(set(value))!=len(value) or any(not isinstance(x,int) or x<=0 for x in value): raise ValueError('系统选择不能重复或为空')
        return value
