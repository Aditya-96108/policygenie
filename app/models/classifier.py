import logging
from transformers import pipeline

logger = logging.getLogger(__name__)
classifier = None

def load_classifier():
    global classifier
    if classifier is None:
        try:
            classifier = pipeline(
                "text-classification",
                model="aditya96k/policy-clause-classifier"
            )
        except Exception as e:
            logger.warning(f"Classifier load error: {e}")
            classifier = None
    return classifier

def classify_clause(text: str) -> list:
    try:
        clf = load_classifier()
        if clf:
            return clf(text)
        return [{"label": "UNKNOWN"}]
    except:
        return [{"label": "UNKNOWN"}]
