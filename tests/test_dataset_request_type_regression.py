"""Request-type regression suite for dataset vocabulary in normal chat.

Dataset/data nouns are topics, not an instruction to launch the research
pipeline.  Keep this broad matrix close to the router so future keyword edits
cannot silently turn questions and recommendations into dataset discovery.
"""
import pytest

from backend.intent_router import classify_intent, handle_intent_message


ML_TASKS = [
    "improve fraud detection", "predict customer churn",
    "build a model to classify emails as spam", "I need to detect anomalies in sensor data",
    "help me train a model for house price prediction", "train a classifier for product review sentiment",
    "build a regression model for energy consumption", "create a model to forecast weekly demand",
    "develop a model to flag phishing emails", "detect defective products in images",
    "train a model for credit risk", "classify support tickets by priority",
    "predict taxi trip duration", "build a recommendation model for movies",
    "forecast electricity load with a model",
]

DATASET_META_QUESTIONS = [
    "give me the best hugging face datasets with links", "what are some popular datasets for NLP",
    "list good datasets for computer vision beginners", "where can I find a dataset for sentiment analysis",
    "what is the Iris dataset", "how many datasets does hugging face have",
    "recommend some datasets I could practice on", "show me beginner-friendly image datasets",
    "which datasets are useful for text classification", "can you list licensed datasets for learning ML",
    "give me some public datasets for a portfolio", "what are good tabular datasets to practice with",
    "recommend datasets for house price prediction", "show me datasets about customer churn",
    "find a dataset for fraud detection",
]

PROCESS_QUESTIONS = [
    "how does your dataset search work", "what data sources do you use", "can you access private datasets",
    "do you verify dataset licenses", "why does a dataset need a target column",
    "can I upload my own data", "what happens after I choose a dataset",
    "how do you rank dataset candidates", "do you download every dataset",
    "can you work with CSV files", "what is your maximum dataset size",
    "how do you handle missing values in uploaded data", "do you train models automatically",
    "can you search Hugging Face", "what metadata do you inspect",
]

ML_ADVICE = [
    "how do I clean messy data", "what's a good way to handle missing values",
    "how to improve accuracy of my model", "explain train/test split",
    "how should I encode categorical data", "why is my validation score lower",
    "what metric should I use for imbalanced classes", "explain cross validation",
    "how do I prevent data leakage", "what is feature engineering",
    "how can I handle outliers", "when should I normalize features",
    "how do I choose a baseline model", "what causes overfitting", "explain precision and recall",
]

BORDERLINE = [
    "I have fraud data, what should I do with it", "find me data about coffee prices",
    "I found a churn dataset, where should I begin", "my data has labels, what now",
    "can this dataset be useful", "I have sensor readings and need advice",
    "what can I learn from customer data", "is my dataset large enough",
    "I have images of defects, what are sensible next steps", "where can I get more examples",
    "I want to explore some sales data", "does this data need cleaning",
    "I have a small dataset for spam", "what should I check before modeling", "can you help me understand my data",
]


@pytest.mark.parametrize("message", ML_TASKS)
def test_explicit_ml_task_starts_research(message):
    assert classify_intent(message, session_id=f"task-{message}") == "RESEARCH_START"


@pytest.mark.parametrize("message", DATASET_META_QUESTIONS + PROCESS_QUESTIONS + ML_ADVICE + BORDERLINE)
def test_dataset_vocabulary_questions_stay_in_normal_answer_path(message):
    assert classify_intent(message, session_id=f"question-{message}") == "EXPLANATION"


def test_dataset_recommendation_is_curated_information_not_a_pipeline(isolate_store):
    response = handle_intent_message("give me the best hugging face datasets with links", session_id="dataset-meta")
    assert response["intent"] == "EXPLANATION"
    assert response["action"] == "NONE"
    assert "https://huggingface.co/datasets/stanfordnlp/imdb" in response["response"]
    assert "matches the goal terms" not in response["response"].lower()
    assert "i'll look for datasets" not in response["response"].lower()
