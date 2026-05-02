from datetime import datetime
from ..ml_utils import (
    predict_startup_success,
    prepare_input,
    get_shap_explanation,
    MODEL_VERSION
)


class EvaluationService:
    COMPETITION_MAP = {
        "emerging": 80,
        "competitive": 150,
        "high": 220,
        "saturated": 300
    }

    INDUSTRY_BASELINE = 60

    @staticmethod
    def process_evaluation(data: dict):

        try:
            funding = float(data["funding"])
            rounds = int(data["rounds"])
            founded_year = int(data["founded_year"])
            country = str(data["country"])
            category = str(data["category"])
            competition_level = str(data["competition_level"])
        except (KeyError, ValueError, TypeError):
            raise ValueError("Invalid input structure.")

        current_year = datetime.now().year

        if funding < 0 or funding > 10_000_000_000:
            raise ValueError("Funding value outside allowed range.")

        if rounds < 0 or rounds > 50:
            raise ValueError("Funding rounds outside allowed range.")

        if founded_year < 1980 or founded_year > current_year:
            raise ValueError("Founded year outside allowed range.")

        if competition_level not in EvaluationService.COMPETITION_MAP:
            raise ValueError("Invalid competition level.")

        if funding > 0 and rounds == 0:
            raise ValueError("Funding provided but rounds set to 0.")

        competition_density = EvaluationService.COMPETITION_MAP[competition_level]

        input_df = prepare_input(
            funding,
            rounds,
            founded_year,
            country,
            category,
            competition_density
        )

        # ✅ FIXED ML CALL
        prediction_result = predict_startup_success(
            funding,
            rounds,
            founded_year,
            country,
            category,
            competition_density
        )

        if prediction_result.get("status") != "success":
            raise ValueError(prediction_result.get("error", "Prediction failed"))

        probability = prediction_result["probability"]
        probability_percent = round(probability * 100, 2)

        rating = EvaluationService._grade(probability_percent)

        difference = round(
            probability_percent - EvaluationService.INDUSTRY_BASELINE,
            2
        )

        shap_features = get_shap_explanation(input_df)

        formatted_features = []
        for item in shap_features:
            try:
                feature = str(item[0])
                value = float(item[1])
                formatted_features.append(
                    (feature.replace("_", " ").title(), round(value, 5))
                )
            except Exception:
                continue

        return {
            "funding": funding,
            "rounds": rounds,
            "founded_year": founded_year,
            "country": country,
            "category": category,
            "competition_level": competition_level,
            "probability": probability_percent,
            "rating": rating,
            "industry_average": EvaluationService.INDUSTRY_BASELINE,
            "difference": difference,
            "top_features": formatted_features,
            "model_version": MODEL_VERSION
        }

    @staticmethod
    def _grade(probability_percent: float) -> str:
        if probability_percent >= 80:
            return "A — Strong Growth Probability"
        elif probability_percent >= 65:
            return "B — Favorable Outlook"
        elif probability_percent >= 50:
            return "C — Moderate Risk Exposure"
        else:
            return "D — Elevated Structural Risk"