PRAGMA foreign_keys=ON;
CREATE TABLE products(product_number TEXT PRIMARY KEY,name TEXT NOT NULL,brand_display TEXT,detail_url TEXT NOT NULL,observed_on TEXT NOT NULL,collection_status TEXT NOT NULL,label_assets_saved INTEGER NOT NULL,recommendation_eligible INTEGER NOT NULL CHECK(recommendation_eligible=0),manufacturer_cross_check TEXT,eligibility_reasons_json TEXT NOT NULL);
CREATE TABLE prices(id INTEGER PRIMARY KEY,product_id TEXT NOT NULL REFERENCES products(product_number),amount INTEGER,currency TEXT,basis TEXT,source_url TEXT,observed_on TEXT,method TEXT);
CREATE TABLE sources(id TEXT PRIMARY KEY,product_id TEXT NOT NULL REFERENCES products(product_number),source_url TEXT NOT NULL,local_path TEXT,sha256 TEXT,observed_on TEXT,published_on TEXT,method TEXT,raw_ocr_text TEXT,missing_reason TEXT);
CREATE TABLE product_fields(product_id TEXT REFERENCES products(product_number),field_name TEXT,value_json TEXT,status TEXT,missing_reason TEXT,raw_text TEXT,source_id TEXT REFERENCES sources(id),PRIMARY KEY(product_id,field_name));
CREATE TABLE label_blocks(id INTEGER PRIMARY KEY,product_id TEXT REFERENCES products(product_number),source_id TEXT REFERENCES sources(id),field_name TEXT,raw_text TEXT,status TEXT,reason TEXT,line_start INTEGER,line_end INTEGER);
CREATE TABLE ingredients(id INTEGER PRIMARY KEY,name_raw TEXT UNIQUE NOT NULL);
CREATE TABLE product_ingredients(id INTEGER PRIMARY KEY,product_id TEXT REFERENCES products(product_number),ingredient_id INTEGER REFERENCES ingredients(id),source_id TEXT REFERENCES sources(id),ordinal INTEGER,parent_id INTEGER REFERENCES product_ingredients(id),amount REAL,unit TEXT,amount_missing_reason TEXT,raw_text TEXT,status TEXT,reason TEXT);
CREATE TABLE nutrient_amounts(id INTEGER PRIMARY KEY,product_id TEXT REFERENCES products(product_number),source_id TEXT REFERENCES sources(id),name_raw TEXT,amount REAL,amount_raw TEXT,unit_raw TEXT,basis_raw TEXT,basis_status TEXT,basis_missing_reason TEXT,nrv_percent_raw TEXT,raw_text TEXT,status TEXT,classification TEXT,reason TEXT,duplicate_source_ids TEXT,operator TEXT);
CREATE TABLE prior_nutrient_evidence(id INTEGER PRIMARY KEY,product_id TEXT REFERENCES products(product_number),name TEXT,amount REAL,unit TEXT,basis TEXT,basis_quantity REAL,raw_text TEXT,source_url TEXT,method TEXT,status TEXT);
CREATE TABLE collection_attempts(id INTEGER PRIMARY KEY,product_id TEXT REFERENCES products(product_number),attempt_date TEXT,method TEXT,result TEXT,source_url TEXT,reason TEXT);
CREATE TABLE reviews(id INTEGER PRIMARY KEY,product_id TEXT REFERENCES products(product_number),review_json TEXT);
CREATE VIEW intake_instructions AS SELECT * FROM label_blocks WHERE field_name='intake';
CREATE VIEW cautions AS SELECT * FROM label_blocks WHERE field_name IN ('cautions','allergen_or_cross_contact','storage');
CREATE VIEW reviewed_nutrients AS SELECT * FROM nutrient_amounts WHERE status='direct_visual';
CREATE INDEX idx_nutrient_name ON nutrient_amounts(name_raw);
CREATE INDEX idx_label_field ON label_blocks(product_id,field_name);
CREATE INDEX idx_ingredients_product ON product_ingredients(product_id);

CREATE TABLE label_reviews(product_id TEXT PRIMARY KEY REFERENCES products(product_number),data_review_status TEXT,reviewed_at TEXT,source_match TEXT,visual_inspection INTEGER,review_json TEXT);
CREATE TABLE field_review_dates(product_id TEXT REFERENCES products(product_number),field_name TEXT,reviewed_at TEXT,PRIMARY KEY(product_id,field_name));
CREATE TABLE correction_history(id INTEGER PRIMARY KEY,product_id TEXT REFERENCES products(product_number),field_name TEXT,old_json TEXT,new_json TEXT,reason TEXT,source_id TEXT REFERENCES sources(id),reviewed_at TEXT);
CREATE VIEW reviewed_ingredients AS SELECT pi.*,i.name_raw FROM product_ingredients pi JOIN ingredients i ON i.id=pi.ingredient_id WHERE pi.status='direct_visual';
CREATE VIEW reviewed_fields AS SELECT * FROM product_fields WHERE status='direct_visual';

-- Product-complete facts, separate from field-level direct observations on held products.
CREATE VIEW verified_product_nutrients AS SELECT n.* FROM reviewed_nutrients n JOIN label_reviews r ON r.product_id=n.product_id WHERE r.data_review_status='verified';
CREATE VIEW verified_product_fields AS SELECT f.* FROM reviewed_fields f JOIN label_reviews r ON r.product_id=f.product_id WHERE r.data_review_status='verified';
CREATE VIEW reviewed_intake_instructions AS SELECT * FROM reviewed_fields WHERE field_name='intake';
CREATE VIEW reviewed_cautions AS SELECT * FROM reviewed_fields WHERE field_name IN ('cautions','storage','allergen_or_cross_contact');

-- Product photography has independent provenance; it does not change label review or recommendation eligibility.
CREATE TABLE product_thumbnails(
 product_id TEXT PRIMARY KEY REFERENCES products(product_number),
 status TEXT NOT NULL CHECK(status IN ('available','unavailable')),
 source_url TEXT,page_url TEXT,local_path TEXT,sha256 TEXT,
 width INTEGER,height INTEGER,observed_on TEXT,missing_reason TEXT,
 image_json TEXT NOT NULL
);
