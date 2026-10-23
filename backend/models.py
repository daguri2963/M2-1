from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

INTERESTS = ('일상의 활력','뼈·근육 건강','장 건강','눈 건강','다양한 성분 보기','잘 모르겠어요')
HABITS = ('식사 시간이 불규칙해요','채소·과일이 적은 편이에요','다양하게 먹는 편이에요','잘 모르겠어요')
CAUTIONS = ('의약품 복용·치료 중이에요','임신·수유 중이에요','알레르기를 확인해야 해요','해당 없어요','잘 모르겠어요')

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Consent(StrictModel):
    provider: Literal['codyssey']
    adultConfirmed: bool
    privacyAccepted: bool
    aiAccepted: bool
    version: str

class Survey(StrictModel):
    interests: list[str] = Field(min_length=1, max_length=6)
    habits: list[str] = Field(min_length=1, max_length=4)
    existing: Literal['없어요','잘 모르겠어요','목록에 없어요','제품 선택']
    productIds: list[str] = Field(default_factory=list, max_length=10)
    cautions: list[str] = Field(min_length=1, max_length=5)
    budget: Literal['','3,000원 이하','5,000원 이하','상관없어요'] = ''
    form: Literal['','정제·캡슐','분말·포','필름·액상','상관없어요'] = ''

    @model_validator(mode='after')
    def validate_choices(self):
        for choices, permitted, exclusive in [(self.interests, INTERESTS, ('잘 모르겠어요',)), (self.habits, HABITS, ('잘 모르겠어요',)), (self.cautions, CAUTIONS, ('해당 없어요','잘 모르겠어요'))]:
            if len(set(choices)) != len(choices) or not set(choices) <= set(permitted):
                raise ValueError('Invalid survey choices')
            if len(choices) > 1 and set(choices).intersection(exclusive):
                raise ValueError('Conflicting survey choices')
        if (self.existing == '제품 선택') != bool(self.productIds):
            raise ValueError('Existing products do not match choice')
        if len(set(self.productIds)) != len(self.productIds):
            raise ValueError('Duplicate product identifiers')
        return self

class Selection(StrictModel):
    productIds: list[str] = Field(min_length=2, max_length=2)

    @model_validator(mode='after')
    def distinct(self):
        if len(set(self.productIds)) != 2:
            raise ValueError('Select two different products')
        return self

class OverlapRequest(StrictModel):
    productIds: list[str] = Field(min_length=1, max_length=10)

class HistoryMessage(StrictModel):
    role: Literal['user','assistant']
    text: str = Field(min_length=1,max_length=1800)

class ChatRequest(StrictModel):
    question: str = Field(min_length=1,max_length=300)
    productId: str | None = None
    survey: Survey | None = None
    history: list[HistoryMessage] = Field(default_factory=list,max_length=8)

class AgentAnswer(StrictModel):
    text: str = Field(min_length=1,max_length=1800)
    citationIds: list[str] = Field(max_length=8)
    productIds: list[str] = Field(default_factory=list,max_length=3)
