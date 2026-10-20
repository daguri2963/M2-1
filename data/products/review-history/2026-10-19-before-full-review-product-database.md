# 다이소 88 SKU 표시정보 데이터베이스

2026-10-19 조사. 실제 SQLite 파일은 `data/products/products.sqlite3`, 함께 읽을 JSON은 `products-normalized.json`이다. 이전 카탈로그의 88개 SKU 식별자를 그대로 유지했다. 일반식품도 포함되어 있으므로 전체를 건강기능식품으로 취급하면 안 된다.

## 확보 범위와 검수 수준

| 구분 | 결과 |
|---|---:|
| 상세페이지 조사 시도 / 원본 이미지 확보 / OCR 수행 SKU | 각각 88 |
| 공식 상세 이미지 출처 레코드 | 137 |
| 원재료 자동 후보 / 직접 대조 행 | 1,238 / 35 |
| 영양·기능성 함량 자동 후보 / 직접 대조 행 | 655 / 96 |
| 일부 구간을 직접 대조한 SKU | 10 |
| 전체 표시 검수 완료 / 추천 적격 SKU | 0 / 0 |

자동 함량 후보 655행 중 50행은 직접 대조 행으로 대체되었다는 상태를 가진 이력이고, 활성 후보는 605행이다. 직접 대조한 96행과 합쳐서 검증된 함량 751행이라고 표현하면 안 된다. 기존 파일의 부분 근거 12행은 별도 이력 테이블에 보존했다.

원재료는 86개에서 자동 구간 후보를 확보했고 누락된 2개는 원본을 직접 대조해 보완했다. 함량은 84개에서 자동 후보를 추출했고 누락된 3개는 직접 대조해 보완했다. 나머지 프로폴리스·아연 필름(610911097)은 관찰한 공식 표시 표에 영양정보가 없어 `not_displayed_in_observed_label`로 기록했다. 성분이 없거나 함량이 0이라는 의미가 아니다.

**이 결과는 88개 전체 표시정보의 확정 전사본이 아니다.** 전체가 `partial_structured` 상태다. 78개는 직접 시각 대조가 남았고, 10개 표본도 일부 구간만 대조했다. 제조사 자체 사이트의 동일 변형 교차확인과 독립 제2검수는 완료하지 않았다. OCR의 표 경계·좌우 열 혼합, 소수점·작은 글자·원료 계층 오독 가능성이 남아 있다. SKU별 현재 상태는 `product-collection-report.md`에 있다.

초기 접근 실패는 재시도로 이미지 확보까지 해결했다. 다만 이미지 확보가 전체 표시의 판독·검수 완료를 뜻하지는 않는다. 별도 제조사 근거를 찾지 못한 경우 다른 용량·변형의 자료를 대신 넣지 않았다.

## 파일과 출처

- `collection-ledger.json`: SKU별 시도, 실패·재시도 사유, 확보 이미지와 구조화 상태.
- `labels/<SKU>/`: 공식 이미지 원본, SHA256 이름, Apple Vision의 로컬 OCR 원문 및 좌표.
- `visual-reviews.json`: 이미지 SHA256에 연결된 부분 시각 대조 결과.
- `products-normalized.json`: 제품·필드·후보·직접 대조·출처를 합친 구조화 결과.
- `nutrient-candidates.csv`: 후보 이력 포함. 반드시 `status` 확인.
- `nutrients-reviewed.csv`: 직접 대조한 96행만 포함.
- `database-validation.json`: 무결성·출처·수치 회귀 검증 결과.

제품번호는 문자열이다. 앞자리 0을 제거하지 않는다. 출처별 공식 URL·로컬 경로·SHA256·관찰일·방법을 저장했다. 발표일은 확인되지 않아 null이며, 이미지 경로의 날짜를 발표일로 사용하지 않았다. 비타민C의 `Ver1.260814`도 표시 버전 원문으로만 보존했다. 가격은 카탈로그 조사 당시 공식 목록 카드의 단품 표시가이며 실시간 재고·현 가격을 보장하지 않는다. 원본 이미지는 내부 근거 확인용으로 보관하며 공개 재배포 권한을 판단한 자료가 아니다.

## 테이블과 조회 원칙

`products`를 중심으로 `prices`, `sources`, `product_fields`, `label_blocks`, `product_ingredients`, `nutrient_amounts`, `collection_attempts`, `reviews`가 제품번호로 연결된다. `ingredients`는 원료 원문 문자열 사전이며 정식 동의어·원료 온톨로지가 아니다. 복합원료는 원문 괄호 묶음을 보존했고, 미표시 배합량은 null과 사유로 남겼다. `prior_nutrient_evidence`는 이전 부분 근거다.

`product_fields`의 값은 JSON 문자열이다. `unverified`는 값 정규화가 남았다는 뜻이며 후보 원문은 `label_blocks`에 있다. `direct_visual`은 해당 행만 원본과 직접 대조했다는 뜻이다. `ocr_candidate`, `ocr_section_candidate`, `ocr_ingredient_candidate`는 자동 후보다. `ocr_candidate_superseded`는 검토 행으로 대체된 후보 이력이다. null은 0으로 변환하지 않는다.

함량은 `amount_raw`, `unit_raw`, `basis_raw`, `operator`, 영양성분 기준치 비율 원문을 함께 보존한다. 단위 변환이나 1정 환산을 하지 않았다. 칼슘 700mg은 4정 기준이고 프레쉬볼 표는 총내용량 2g 기준이다. LG의 나트륨·당류·단백질 ‘미만’은 `<`로 보존했다. μg DFE·μg RAE·mg α-TE·mg NE·CFU와 IU를 단순 질량 단위로 합산하면 안 된다. 미확인 섭취 기준에는 사유가 있다.

직접 대조한 함량만 조회하려면 다음 뷰를 사용한다. 출처를 같이 확인하고, 이 결과만으로 제품 전체가 검수 완료라고 판단하지 않는다.

```sql
SELECT n.product_id, p.name, n.name_raw, n.operator, n.amount_raw,
       n.unit_raw, n.basis_raw, s.source_url
FROM reviewed_nutrients n
JOIN products p ON p.product_number = n.product_id
JOIN sources s ON s.id = n.source_id
ORDER BY n.product_id, n.name_raw;
```

```sql
-- 미확정 필드와 누락 사유
SELECT product_id, field_name, status, missing_reason
FROM product_fields WHERE status <> 'direct_visual';
-- 같은 성분이어도 기준과 단위를 유지해 비교
SELECT product_id, amount_raw, unit_raw, basis_raw
FROM reviewed_nutrients WHERE name_raw = '칼슘';
```

`intake_instructions`, `cautions` 뷰는 자동 원문 구간 후보이며 확정 안내가 아니다. 직접 대조한 섭취법·주의사항은 `product_fields WHERE status='direct_visual'`로 조회한다. 전체 제품의 추천 적격 값은 false다.

## 재생성 및 검증

프로젝트 루트에서 Python 3 표준 라이브러리만으로 오프라인 재생성할 수 있다.

```sh
python3 scripts/build_product_database.py
python3 scripts/validate_product_database.py
```

검증기는 88개 식별자, JSON/SQLite 행 수, 외래키·무결성, 이미지 SHA256, 동일 제품 출처 연결, 누락 사유, 수치·단위·기준, 상한 기호, CSV 행 수를 검사한다. 이는 원문 전체를 사람이 검수한 시험이 아니다.

OCR를 다시 생성하려면 macOS Swift와 Vision이 필요하다. 이미 성공한 OCR 파일은 건너뛴다. 로컬 Vision 실행이 환경 제한으로 실패할 수 있으며, 원본 및 기존 성공 결과는 그대로 보존한다.

```sh
swiftc -module-cache-path /private/tmp/m2-swift-cache scripts/ocr_labels.swift -o /private/tmp/m2-ocr-label
python3 scripts/ocr_saved_labels.py
```

`import_label_assets.py`는 관찰한 브라우저 자산 목록의 로컬 파일을 수입하는 도구다. 별도 네트워크 API를 추측해 수집하지 않는다. 재수입 시 수집 원장의 상태가 다시 수집 단계로 갱신될 수 있으므로, 기존 원장과 시각 대조 기록을 보존하고 구조화 결과를 다시 검증해야 한다.
