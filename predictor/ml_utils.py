import os
import joblib
import numpy as np
import pandas as pd
import logging
from datetime import datetime
from django.conf import settings

# ==========================================================
# LOGGING CONFIGURATION
# ==========================================================

logger = logging.getLogger(__name__)

# ==========================================================
# MODEL CONFIGURATION
# ==========================================================

MODEL_VERSION = "3.0.0-production"

MODEL_DIR = os.path.join(settings.BASE_DIR, "ml_models")

MODEL_PATH = os.path.join(MODEL_DIR, "startup_model_production.pkl")
FEATURE_PATH = os.path.join(MODEL_DIR, "feature_columns_production.pkl")
THRESHOLD_PATH = os.path.join(MODEL_DIR, "threshold.pkl")

# ==========================================================
# LOAD MODEL ARTIFACTS
# ==========================================================

try:
    model = joblib.load(MODEL_PATH)
    feature_columns = joblib.load(FEATURE_PATH)

    raw_threshold = joblib.load(THRESHOLD_PATH)

    if isinstance(raw_threshold, (list, np.ndarray)):
        threshold = float(raw_threshold[0])
    else:
        threshold = float(raw_threshold)

    logger.info("Model loaded successfully")

except Exception as e:
    logger.error(f"Model loading failed: {str(e)}")
    raise RuntimeError("ML model failed to load")

# ==========================================================
# SHAP SAFE (LAZY LOADING - IMPORTANT FIX)
# ==========================================================

explainer = None
shap = None

def init_shap():
    """
    Lazy SHAP loader to prevent Render crash
    """
    global shap, explainer

    if explainer is not None:
        return

    try:
        import shap as shap_lib
        shap = shap_lib
        explainer = shap.TreeExplainer(model)
        logger.info("SHAP initialized successfully")

    except Exception as e:
        shap = None
        explainer = None
        logger.warning(f"SHAP disabled safely: {str(e)}")


# ==========================================================
# INPUT VALIDATION
# ==========================================================

def validate_inputs(funding, rounds, founded_year, country, category, competition_density):

    errors = []

    if funding < 0:
        errors.append("Funding cannot be negative")

    if rounds < 0:
        errors.append("Funding rounds cannot be negative")

    current_year = datetime.now().year

    if founded_year < 1900 or founded_year > current_year:
        errors.append("Invalid founded year")

    if competition_density < 0:
        errors.append("Competition density cannot be negative")

    if not country:
        errors.append("Country is required")

    if not category:
        errors.append("Category is required")

    if errors:
        raise ValueError(", ".join(errors))


# ==========================================================
# INPUT PREPARATION
# ==========================================================

def prepare_input(funding, rounds, founded_year, country, category, competition_density):

    current_year = datetime.now().year
    startup_age = current_year - founded_year

    log_funding = np.log1p(funding)
    funding_per_round = funding / (rounds + 1)

    input_dict = {col: 0.0 for col in feature_columns}

    input_dict["funding_rounds"] = rounds
    input_dict["startup_age"] = startup_age
    input_dict["founded_year"] = founded_year
    input_dict["log_funding"] = log_funding
    input_dict["funding_per_round"] = funding_per_round
    input_dict["competition_density"] = competition_density

    country_col = f"country_code_{country}"
    if country_col in input_dict:
        input_dict[country_col] = 1
    else:
        logger.warning(f"Unknown country: {country}")

    category_col = f"main_category_{category}"
    if category_col in input_dict:
        input_dict[category_col] = 1
    else:
        logger.warning(f"Unknown category: {category}")

    return pd.DataFrame([input_dict])


# ==========================================================
# PREDICTION ENGINE
# ==========================================================

def predict_startup_success(funding, rounds, founded_year, country, category, competition_density):

    try:
        validate_inputs(funding, rounds, founded_year, country, category, competition_density)

        input_df = prepare_input(
            funding,
            rounds,
            founded_year,
            country,
            category,
            competition_density
        )

        probability = float(model.predict_proba(input_df)[0][1])
        prediction = "Likely to Succeed" if probability >= threshold else "High Risk"

        return {
            "probability": probability,
            "prediction": prediction,
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Prediction failed: {str(e)}")
        return {
            "error": str(e),
            "status": "failed"
        }


# ==========================================================
# SHAP EXPLANATION (SAFE + LAZY INIT)
# ==========================================================

def get_shap_explanation(input_df, top_n=10):

    try:
        init_shap()

        if explainer is None:
            return []

        shap_output = explainer(input_df)

        shap_values = shap_output.values if hasattr(shap_output, "values") else shap_output

        if len(shap_values.shape) == 3:
            shap_values = shap_values[:, :, 1]

        shap_values = shap_values[0]

        contributions = [
            (feature, float(value))
            for feature, value in zip(input_df.columns, shap_values)
        ]

        contributions.sort(key=lambda x: abs(x[1]), reverse=True)

        return contributions[:top_n]

    except Exception as e:
        logger.warning(f"SHAP failed safely: {str(e)}")
        return []


# ==========================================================
# GLOBAL FEATURE IMPORTANCE
# ==========================================================

def get_global_feature_importance(top_n=10):

    try:
        if hasattr(model, "feature_importances_"):

            importances = model.feature_importances_

            return sorted(
                zip(feature_columns, importances),
                key=lambda x: x[1],
                reverse=True
            )[:top_n]

        return []

    except Exception as e:
        logger.warning(f"Feature importance failed: {str(e)}")
        return []