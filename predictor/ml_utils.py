import os
import logging
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
from django.conf import settings

# ==========================================================
# LOGGING
# ==========================================================

logger = logging.getLogger(__name__)

# ==========================================================
# MODEL CONFIG
# ==========================================================

MODEL_VERSION = "3.0.0-production"

MODEL_DIR = os.path.join(settings.BASE_DIR, "ml_models")

MODEL_PATH = os.path.join(MODEL_DIR, "startup_model_production.pkl")
FEATURE_PATH = os.path.join(MODEL_DIR, "feature_columns_production.pkl")
THRESHOLD_PATH = os.path.join(MODEL_DIR, "threshold.pkl")

# ==========================================================
# SAFE GLOBALS (IMPORTANT FOR RENDER)
# ==========================================================

model = None
feature_columns = []
threshold = 0.5

explainer = None
shap = None

# ==========================================================
# SAFE MODEL LOADING (NO CRASH ON IMPORT)
# ==========================================================

try:
    model = joblib.load(MODEL_PATH)
    feature_columns = joblib.load(FEATURE_PATH)

    raw_threshold = joblib.load(THRESHOLD_PATH)

    if isinstance(raw_threshold, (list, tuple, np.ndarray)):
        threshold = float(raw_threshold[0])
    else:
        threshold = float(raw_threshold)

    logger.info("✅ Model loaded successfully")

except Exception as e:
    logger.error(f"❌ Model loading failed: {e}")

    # DO NOT CRASH RENDER
    model = None
    feature_columns = []
    threshold = 0.5


# ==========================================================
# SHAP LAZY INIT (SAFE)
# ==========================================================

def init_shap():
    global shap, explainer, model

    if explainer is not None or model is None:
        return

    try:
        import shap as shap_lib
        shap = shap_lib
        explainer = shap.TreeExplainer(model)
        logger.info("✅ SHAP initialized")

    except Exception as e:
        shap = None
        explainer = None
        logger.warning(f"⚠️ SHAP disabled: {e}")


# ==========================================================
# VALIDATION
# ==========================================================

def validate_inputs(funding, rounds, founded_year, country, category, competition_density):

    current_year = datetime.now().year
    errors = []

    if funding is None or funding < 0:
        errors.append("Invalid funding")

    if rounds is None or rounds < 0:
        errors.append("Invalid rounds")

    if founded_year < 1900 or founded_year > current_year:
        errors.append("Invalid founded year")

    if competition_density is None or competition_density < 0:
        errors.append("Invalid competition density")

    if not country:
        errors.append("Country required")

    if not category:
        errors.append("Category required")

    if errors:
        raise ValueError(", ".join(errors))


# ==========================================================
# INPUT PREP
# ==========================================================

def prepare_input(funding, rounds, founded_year, country, category, competition_density):

    current_year = datetime.now().year
    startup_age = current_year - founded_year

    log_funding = np.log1p(funding)
    funding_per_round = funding / (rounds + 1)

    # SAFE fallback if model not loaded
    cols = feature_columns if feature_columns else []

    input_dict = {col: 0.0 for col in cols}

    input_dict.update({
        "funding_rounds": rounds,
        "startup_age": startup_age,
        "founded_year": founded_year,
        "log_funding": log_funding,
        "funding_per_round": funding_per_round,
        "competition_density": competition_density,
    })

    country_col = f"country_code_{country}"
    if country_col in input_dict:
        input_dict[country_col] = 1

    category_col = f"main_category_{category}"
    if category_col in input_dict:
        input_dict[category_col] = 1

    return pd.DataFrame([input_dict])


# ==========================================================
# MAIN PREDICTION (FAIL SAFE)
# ==========================================================

def predict_startup_success(funding, rounds, founded_year, country, category, competition_density):

    try:
        if model is None:
            return {
                "status": "failed",
                "error": "Model not loaded (deployment issue)"
            }

        validate_inputs(funding, rounds, founded_year, country, category, competition_density)

        input_df = prepare_input(
            funding, rounds, founded_year,
            country, category, competition_density
        )

        proba = model.predict_proba(input_df)[0][1]
        probability = float(proba)

        prediction = "Likely to Succeed" if probability >= threshold else "High Risk"

        return {
            "status": "success",
            "probability": probability,
            "prediction": prediction,
        }

    except Exception as e:
        logger.error(f"Prediction error: {e}")

        return {
            "status": "failed",
            "error": str(e),
            "probability": 0.0,
            "prediction": "Error"
        }


# ==========================================================
# SHAP EXPLANATION (SAFE)
# ==========================================================

def get_shap_explanation(input_df, top_n=10):

    try:
        init_shap()

        if explainer is None:
            return []

        shap_output = explainer(input_df)
        values = shap_output.values if hasattr(shap_output, "values") else shap_output

        if len(values.shape) == 3:
            values = values[:, :, 1]

        values = values[0]

        contributions = list(zip(input_df.columns, values))
        contributions.sort(key=lambda x: abs(x[1]), reverse=True)

        return [(k, float(v)) for k, v in contributions[:top_n]]

    except Exception as e:
        logger.warning(f"SHAP error ignored: {e}")
        return []


# ==========================================================
# FEATURE IMPORTANCE (SAFE)
# ==========================================================

def get_global_feature_importance(top_n=10):

    try:
        if model is None:
            return []

        if hasattr(model, "feature_importances_"):

            importances = model.feature_importances_

            return sorted(
                zip(feature_columns, importances),
                key=lambda x: x[1],
                reverse=True
            )[:top_n]

        return []

    except Exception as e:
        logger.warning(f"Feature importance error: {e}")
        return []