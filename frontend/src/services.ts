import productData from './data/products.json';
import type {Survey} from './domain';
export type Product=typeof productData[number];
export type ChatContext={productId?:string;interests:string[]};
export type ChatReply={text:string;productId?:string};
export interface SelectionService { examples(survey:Survey):Promise<Product[]>; reply(question:string,context:ChatContext):Promise<ChatReply> }
export const products:Product[]=productData;
export const featuredIds=['600000128','600000129','600000147','610911092','600000313','601678603','610911097','032306200'];
export const featured=featuredIds.map(id=>products.find(p=>p.id===id)!).filter(Boolean);
export const getProduct=(id:string)=>products.find(p=>p.id===id);
export const mockService:SelectionService={
 async examples(_survey){return ['032306200','610911092','600000128'].map(id=>getProduct(id)!);},
 async reply(question,context){
  const p=context.productId?getProduct(context.productId):undefined;
  if(p)return {text:`‘${p.name}’의 검수된 표시를 함께 볼게요.\n\n표시 섭취방법: ${p.intake||'표시 확인이 필요해요.'}\n\n함량은 각 제품의 기준량과 단위를 함께 읽어야 해요. 개인별 섭취 적합성이나 병용 가능 여부는 이 화면 체험에서 판단하지 않아요. 상세 화면에서 주의사항 전체를 확인해 주세요.`,productId:p.id};
  if(/차이|비교|함량/.test(question))return {text:'함량 숫자 옆의 단위와 기준량을 먼저 확인해 보세요. ‘1정당’과 ‘하루 4정당’, ‘총내용량당’은 같은 기준이 아니에요.\n\n비교 화면에서 두 제품의 기준을 나란히 확인할 수 있어요. 기준이 다르면 함량을 자동 환산하거나 우열을 정하지 않아요.'};
  if(/처음|시작|골라/.test(question))return {text:'처음이라면 관심 분야를 정하고, 이미 먹는 제품이 있는지 확인한 뒤 제품 표시를 읽어 보세요.\n\n이 체험에서는 설문을 입력해도 개인에게 맞춘 추천을 계산하지 않아요. 준비된 예시 제품으로 성분·기준량·주의사항을 살펴보고 비교하는 흐름을 체험할 수 있어요.'};
  return {text:'이 답변은 미리 작성한 화면 체험 안내예요. 실시간 AI와 연결되어 있지 않아 질문에 대한 개인화된 판단은 제공하지 않아요.\n\n제품을 고를 때는 식품유형, 성분의 단위·기준량, 표시 섭취방법과 주의사항을 함께 확인해 주세요. 제품 상세에서 검수된 정보와 공식 출처를 볼 수 있어요.'};
 }
};
