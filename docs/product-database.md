# 다이소 88 SKU 표시정보 데이터베이스

2026-10-20 (Asia/Seoul) 전수 표시 검수 반영. `data/products/products.sqlite3`는 실제 조회 가능한 SQLite이며 `products-normalized.json`과 같은 결과를 담는다. 기존 카탈로그 88개 품번을 유지했다. 일반식품과 건강기능식품은 `food_type`으로 구분한다.

## 현재 결과

| 항목 | 결과 |
|---|---:|
| 실제 공식 표시 이미지 시각 대조 제품 | 88 |
| 제품 전체 표시 검수 완료 / 보류 | 87 / 1 |
| 원본 상세 이미지 / 추가 공식 상품 화면 | 137 / 1 |
| 직접 대조 원료 원문 묶음 / 정량 행 | 1,522 / 913 |
| 보존한 OCR 원료 후보 / 함량 후보 | 1,238 / 655 |
| 완료 제품만의 정량 행 | 908 |
| 추천 로직 평가·적격 제품 | 미실시 / 0 |

같은 수행자가 실제 이미지와 값을 대조한 자체 검수다. 독립 제2검수는 하지 않았다. 제조사 자체 사이트에서 동일 변형을 추가 확인하지 못한 사실을 남겼으나, 그것만으로 공식 다이소 표시를 직접 확인한 제품을 보류하지 않았다. 상세 표시의 정확한 전사는 현재 실물 포장이나 규제기관 신고의 최신성까지 확인했다는 뜻은 아니다.

보류는 **600651654 산뜻해질 유한 생유산균 캡슐** 1개다. 공식 제품정보표가 `프로바이오틱스 수 (수량 기재 안됨)`으로 표시되어 있다. 같은 상세의 광고에는 100억 CFU 투입·20억 CFU 보장이 있으나, 이를 영양표의 확정 정량으로 대입하지 않았다. 광고 근거와 보류 사유는 별도 저장했다. 다른 표시 항목과 명시된 일반 영양 5행은 직접 확인된 사실로 남긴다.

## 출처와 날짜

`label-review-ledger.json`이 88개 검수 결정의 원장이다. 원본 SHA256·URL·관찰일, 크롭 좌표, 실제 검수일, 품명·변형·포장 매칭, 항목별 상태, 보류 사유를 보존했다. 검수 완료 기준은 원장의 `completion_criteria`에 있다. 실제 이미지에 품번이 없는 경우에는 공식 상세의 품번 연결과 이미지의 제품명·변형·포장을 대조했다. 모든 이미지에 품번이 인쇄되었다고 간주하지 않는다.

원본과 가격의 관찰일은 2026-10-19를 유지한다. 검수일은 2026-10-19~20의 실제 일시다. 032306200의 판매 포장 12정은 2026-10-20 공식 화면의 상품명과 품번을 새로 확인해 별도 출처로 연결했다. 원본 영양표는 1정 600 mg을 뒷받침한다. 발행일은 미확인이므로 null이다. URL 폴더의 날짜를 발행일로 사용하지 않았다.

## 파일

- `products.sqlite3`, `products-normalized.json`: 현재 통합 결과.
- `label-review-ledger.json`: 전수 시각 대조 결정과 필드별 상태.
- `label-review-corrections.json`: 초기 추출값/부분 대조값 대비 현재 값, 이유·출처·검수일. 값 보완과 상태 승격도 포함하므로 모두 오독 건수로 세지 않는다.
- `review-history/`: 초기 결과, 중간 배치 결정, 최종 결정 스냅샷. 과거 문서도 보존했다.
- `review-evidence/index.json`, 크롭 PNG: 원본 출처와 좌표에 연결한 판독 근거. `field-drafts.json`은 미검수 OCR 초안이며 확정 데이터로 사용하지 않는다.
- `labels/<SKU>/`: 공식 이미지 원본과 로컬 OCR 원문·좌표.
- `collection-ledger.json`: 최초 수집·재시도 이력과 현재 검수 상태.
- `visual-reviews.json`: 초기 10개 부분 대조의 과거 근거.
- `nutrients-reviewed.csv`: 필드 수준 직접 대조 정량 913행. 보류 제품의 명시 영양 5행도 포함한다.
- `nutrient-candidates.csv`: 기존 OCR 후보 655행, 모두 확정 조회에서 제외된 이력.
- `database-validation.json`: 무결성·출처·직렬화·수치 회귀 검증 결과.

원료는 쉼표를 분리하되 복합원료 괄호·원산지·캡슐기제 묶음과 순서를 원문 문자열로 보존했다. 별도 하위 원료 온톨로지나 배합량을 추정하지 않았다. 원료 정량 null과 사유를 유지한다. 전사에서는 줄바꿈과 일부 문장부호·띄어쓰기를 읽기 쉽게 정리했으며 원본 이미지를 최종 근거로 보존한다.

## 테이블과 조회

`products`, `sources`, `prices`, `product_fields`, `product_ingredients`, `nutrient_amounts`는 품번으로 연결된다. `label_reviews`는 제품 전체 검수 상태와 원장 사본, `field_review_dates`는 필드 검수일, `correction_history`는 이전·이후 값을 담는다. `label_blocks`와 `prior_nutrient_evidence`는 과거 추출 근거다. 품번은 문자열로 저장해 앞자리 0을 유지한다.

`verified`는 필수 표시 항목을 모두 직접 확인하거나 미표시·해당 없음 사유를 기록했고, 명시적으로 전수 검수 완료를 결정했으며, 미해결 차단 사유가 없다는 뜻이다. `on_hold`는 미해결 사유가 있다. `not_displayed_in_observed_label`은 관찰한 표시의 부재이며 성분량 0과 다르다. 프로폴리스·아연 필름(610911097)의 영양표가 이에 해당한다.

| 뷰 | 범위 |
|---|---|
| `reviewed_nutrients` | 직접 대조한 정량 913행, 필드 수준 사실 |
| `verified_product_nutrients` | 제품 전체 검수 완료 87개의 정량 908행 |
| `reviewed_fields`, `reviewed_ingredients` | 직접 대조한 필드·원료 묶음 |
| `verified_product_fields` | 제품 전체 검수 완료인 직접 대조 필드 |
| `reviewed_intake_instructions`, `reviewed_cautions` | 직접 대조한 섭취·주의·보관·알레르기 표시 |
| `intake_instructions`, `cautions` | 과거 자동 구간 후보. 확정 안내에 사용하지 않음 |

```sql
SELECT n.product_id, p.name, n.name_raw, n.operator, n.amount_raw,
       n.unit_raw, n.basis_raw, s.source_url
FROM verified_product_nutrients n
JOIN products p ON p.product_number=n.product_id
JOIN sources s ON s.id=n.source_id;

SELECT product_id, data_review_status, reviewed_at, review_json
FROM label_reviews WHERE data_review_status<>'verified';
```

`amount_raw`, `unit_raw`, `basis_raw`, `operator`, 기준치 비율을 함께 사용한다. IU·CFU·RAE·DFE·NE·α-TE를 다른 단위와 임의 합산하지 않는다. 총내용량 기준을 1일 기준으로 바꾸지 않았다. `50억`을 숫자 5,000,000,000으로 표현한 경우도 원문과 CFU를 보존하며 질량으로 환산하지 않는다. 칼슘 700 mg은 4정 기준, 판비틴 비오틴 70,000 μg은 총 14포 기준이다. ‘미만’은 `<`로 보존했다.

추천 정책과 사용자 조건 로직은 사용자 요청에 따라 이후 작업으로 남겼다. 표시 검수 완료 여부와 `recommendation_eligible=false`는 별개다.

## 재생성과 검증

Python 3 표준 라이브러리로 오프라인 재생성한다.

```sh
python3 scripts/build_product_database.py
python3 scripts/validate_product_database.py
```

검증기는 품번 전수 일치, SHA256·공식 출처, 외래키·무결성, JSON/SQLite 필드와 정량·원료 행 일치, 검수 게이트, 보류 제품 제외, 소수점·단위·기준·상한 회귀를 검사한다. 자동 검사는 별도 사람의 독립 시각 검수를 대신하지 않는다.

`import_label_assets.py` 재수입은 수집 단계 상태를 되돌릴 수 있다. 기존 원장·근거를 보존하고 빌드와 검증을 다시 수행해야 한다. OCR 재실행은 이번 검수에 필요하지 않다.

## 공식 썸네일 확장 (2026-10-21)

`product_thumbnails` 테이블은 88개 품번의 사진 상태, 공식 이미지 URL·관찰 페이지, 로컬 경로, SHA256, 크기·해상도·확인일을 저장한다. 전체 수집 메타데이터는 `image_json`에 함께 보존한다. 정규화 JSON 스키마 0.4의 제품별 `thumbnail`과 동일하다. 사진 수집은 표시정보 검수와 별개이며 기존 검수 상태·날짜·추천 적격 판정을 바꾸지 않는다. [수집 기록](product-thumbnails.md)을 참조한다.
