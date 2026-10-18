import os
import json
import re
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.base import BaseEstimator, TransformerMixin

# Map detailed CORD categories to core extraction target classes
CATEGORY_MAPPING = {
    "menu.nm": "ITEM_NAME",
    "menu.sub_nm": "ITEM_NAME",
    "menu.price": "ITEM_PRICE",
    "menu.unitprice": "ITEM_PRICE",
    "menu.sub_price": "ITEM_PRICE",
    "menu.cnt": "ITEM_QTY",
    "menu.sub_cnt": "ITEM_QTY",
    "total.total_price": "TOTAL_PRICE",
    "sub_total.subtotal_price": "SUBTOTAL_PRICE",
    "sub_total.tax_price": "TAX_PRICE",
    "sub_total.service_price": "SERVICE_CHARGE",
    "total.cashprice": "CASH_PAID",
    "total.changeprice": "CHANGE_DUE",
    "total.creditcardprice": "CARD_PAID",
    "menu.discountprice": "DISCOUNT",
    "sub_total.discount_price": "DISCOUNT",
}

class ReceiptFeatureExtractor(BaseEstimator, TransformerMixin):
    """Extracts structural and lexical features from receipt lines."""
    def fit(self, X, y=None):
        return self

    def transform(self, X):
        features = []
        for text in X:
            text_str = str(text).strip()
            length = len(text_str)
            digits = sum(c.isdigit() for c in text_str)
            alphas = sum(c.isalpha() for c in text_str)
            upper = sum(c.isupper() for c in text_str)
            spaces = sum(c.isspace() for c in text_str)
            has_dot = "." in text_str
            has_comma = "," in text_str
            
            # Keyword flags
            lower = text_str.lower()
            is_total_kw = any(w in lower for w in ["total", "ttl", "net", "amount due", "grand total", "balance"])
            is_subtotal_kw = any(w in lower for w in ["subtotal", "sub total", "sub-total"])
            is_tax_kw = any(w in lower for w in ["tax", "gst", "cgst", "sgst", "vat", "pb1", "sc"])
            is_service_kw = any(w in lower for w in ["service", "svc", "charge", "tip"])
            is_cash_kw = any(w in lower for w in ["cash", "tunai", "bayar"])
            is_change_kw = any(w in lower for w in ["change", "kembali"])
            is_qty_kw = bool(re.match(r"^x?\d+\s*x?$", lower)) or "qty" in lower
            is_pure_num = text_str.replace(".", "").replace(",", "").replace("-", "").isdigit()

            features.append([
                length,
                digits / (length + 1e-5),
                alphas / (length + 1e-5),
                upper / (alphas + 1e-5),
                spaces,
                int(has_dot),
                int(has_comma),
                int(is_total_kw),
                int(is_subtotal_kw),
                int(is_tax_kw),
                int(is_service_kw),
                int(is_cash_kw),
                int(is_change_kw),
                int(is_qty_kw),
                int(is_pure_num),
            ])
        return np.array(features)

def prepare_dataset(csv_path: str):
    df = pd.read_csv(csv_path)
    df = df.dropna(subset=["text", "category"])
    
    # Map categories to consolidated classes
    df["target_class"] = df["category"].map(CATEGORY_MAPPING).fillna("OTHER")
    
    # Filter out empty or whitespace text
    df["text"] = df["text"].astype(str).str.strip()
    df = df[df["text"].str.len() > 0]
    
    return df

def train_model():
    base_dir = Path(__file__).resolve().parent.parent
    csv_path = base_dir / "cord_receipts.csv"
    output_model_path = base_dir / "alibi" / "data" / "cord_receipt_classifier.joblib"
    
    if not csv_path.exists():
        print(f"Error: {csv_path} not found.")
        return

    print(f"Loading CORD receipt annotations from {csv_path}...")
    df = prepare_dataset(str(csv_path))
    print(f"Total labeled samples: {len(df)}")
    print("Class distribution:")
    print(df["target_class"].value_counts())

    train_df = df[df["split"] == "train"]
    test_df = df[df["split"].isin(["dev", "test"])]
    if len(train_df) == 0:
        # If splits are not defined, random split
        from sklearn.model_selection import train_test_split
        train_df, test_df = train_test_split(df, test_size=0.2, random_state=42, stratify=df["target_class"])

    X_train = train_df["text"]
    y_train = train_df["target_class"]
    X_test = test_df["text"]
    y_test = test_df["target_class"]

    # Hybrid Pipeline combining TF-IDF Char/Word n-grams with engineered structural features
    pipeline = Pipeline([
        ("features", FeatureUnion([
            ("word_tfidf", TfidfVectorizer(ngram_range=(1, 3), analyzer="word", min_df=2)),
            ("char_tfidf", TfidfVectorizer(ngram_range=(2, 5), analyzer="char_wb", min_df=2)),
            ("struct_feats", ReceiptFeatureExtractor())
        ])),
        ("classifier", LogisticRegression(max_iter=1000, C=5.0, class_weight="balanced"))
    ])

    print("\nTraining machine learning classifier on CORD dataset...")
    pipeline.fit(X_train, y_train)

    print("\nEvaluating on evaluation split...")
    y_pred = pipeline.predict(X_test)
    report = classification_report(y_test, y_pred, digits=3)
    print(report)

    output_model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, output_model_path)
    print(f"\nModel successfully trained and saved to: {output_model_path}")

    # Also build canonical few-shot receipt examples from CORD ground truth JSON for the Multimodal LLM
    build_few_shot_dataset(base_dir)

def build_few_shot_dataset(base_dir: Path):
    """Extract canonical diverse few-shot prompt examples from CORD ground truth."""
    few_shot_path = base_dir / "alibi" / "data" / "cord_few_shots.json"
    cord_train_json = base_dir / "cord_data" / "CORD" / "train" / "json"
    
    if not cord_train_json.exists():
        return

    examples = []
    # Pick 5 diverse well-formed receipts from CORD
    sample_ids = ["receipt_00000", "receipt_00001", "receipt_00004", "receipt_00010", "receipt_00020"]
    for sid in sample_ids:
        jpath = cord_train_json / f"{sid}.json"
        if not jpath.exists():
            continue
        try:
            with open(jpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            items = []
            taxes = []
            total = 0.0
            merchant = "STORE"
            for line in data.get("valid_line", []):
                cat = line.get("category", "")
                words = " ".join(w.get("text", "") for w in line.get("words", []))
                if "nm" in cat and not items and len(words) > 3:
                    merchant = words
                elif "price" in cat and "total" in cat:
                    val = re.sub(r"[^\d.]", "", words.replace(",", "."))
                    if val:
                        try:
                            total = float(val)
                        except Exception:
                            pass
                elif "menu.nm" in cat:
                    items.append({"description": words, "quantity": 1.0, "total": 0.0, "category": "Food"})
            
            if items and total > 0:
                examples.append({
                    "receipt_id": sid,
                    "merchant": merchant,
                    "total": total,
                    "sample_items_count": len(items)
                })
        except Exception:
            pass

    with open(few_shot_path, "w", encoding="utf-8") as f:
        json.dump(examples, f, indent=2)
    print(f"Few-shot examples saved to: {few_shot_path}")

if __name__ == "__main__":
    train_model()
