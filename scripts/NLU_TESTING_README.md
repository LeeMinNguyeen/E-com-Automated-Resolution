# NLU Model Accuracy Testing Guide

## Overview

The `test_nlu_accuracy.py` script evaluates the Multi-Task DistilBERT NLU model using standard deep learning evaluation metrics.

## Metrics Calculated

### Classification Metrics

#### Intent Classification
- **Accuracy**: Overall correctness (TP+TN)/(TP+TN+FP+FN)
- **Balanced Accuracy**: Adjusted for class imbalance
- **Precision (Weighted)**: Weighted by class support
- **Recall (Weighted)**: Weighted by class support
- **F1-Score (Weighted)**: Harmonic mean of precision and recall
- **Macro Metrics**: Treats all classes equally (unweighted average)
- **Per-Class Metrics**: Individual metrics for each intent
- **Confusion Matrix**: Visual representation of predictions

#### Sentiment Analysis
- Same metrics as intent classification
- Applied to positive/negative/neutral sentiment

### Confidence Score Analysis
- **Mean Confidence**: Average confidence across predictions
- **Standard Deviation**: Confidence score variability
- **Min/Max**: Range of confidence scores
- **Median**: Middle confidence value
- **High Confidence %**: Percentage of predictions with >80% confidence

## Usage

### Basic Usage (Sample Data)
```bash
python scripts/test_nlu_accuracy.py
```

This uses built-in sample test data with ~50 test cases covering:
- All intents (track_order, refund, delivery_delay, etc.)
- All sentiments (positive, negative, neutral)
- Edge cases (very negative, ambiguous texts)

### With Custom Test Data
```bash
python scripts/test_nlu_accuracy.py --test-file data/my_test_set.csv
```

**CSV Format:**
```csv
text,intent_label,sentiment_label
"Where is my order?",track_order,neutral
"I want a refund!",request_refund,negative
"Thank you!",provide_feedback_on_service,positive
```

### Save Results
```bash
# Results saved to results/ directory by default
python scripts/test_nlu_accuracy.py

# Specify custom output directory
python scripts/test_nlu_accuracy.py --output-dir my_results/

# Don't save results (print only)
python scripts/test_nlu_accuracy.py --no-save
```

## Output Files

When saved, the script generates:

1. **Metrics JSON** (`nlu_metrics_YYYYMMDD_HHMMSS.json`)
   - All calculated metrics
   - Per-class breakdown
   - Confidence statistics
   - Test metadata

2. **Predictions CSV** (`nlu_predictions_YYYYMMDD_HHMMSS.csv`)
   - All test samples
   - True labels
   - Predicted labels
   - Confidence scores

3. **Confusion Matrices** (PNG images)
   - `confusion_matrix_intent_YYYYMMDD_HHMMSS.png`
   - `confusion_matrix_sentiment_YYYYMMDD_HHMMSS.png`

## Understanding the Metrics

### Accuracy
- **Range**: 0-1 (0-100%)
- **Interpretation**: 
  - >90%: Excellent
  - 80-90%: Good
  - 70-80%: Fair
  - <70%: Needs improvement

### Precision
- **Definition**: Of all positive predictions, how many were correct?
- **Formula**: TP / (TP + FP)
- **High Precision**: Few false positives

### Recall
- **Definition**: Of all actual positives, how many were found?
- **Formula**: TP / (TP + FN)
- **High Recall**: Few false negatives

### F1-Score
- **Definition**: Harmonic mean of precision and recall
- **Formula**: 2 × (Precision × Recall) / (Precision + Recall)
- **Balanced metric**: Good when both precision and recall are important

### Weighted vs Macro
- **Weighted**: Accounts for class imbalance (more samples = more weight)
- **Macro**: Treats all classes equally (better for imbalanced datasets)

### Balanced Accuracy
- Average of recall for each class
- Better than accuracy for imbalanced datasets
- Prevents "always predict majority class" bias

## Sample Test Data Included

The script includes 50+ test samples:

### Intents Covered
- `track_order` (7 samples)
- `report_delivery_delay` (6 samples)
- `report_order_content_issue` (6 samples)
- `request_refund` (8 samples)
- `provide_feedback_on_service` (8 samples)
- `other` (7 samples)

### Sentiment Distribution
- Positive: ~15%
- Negative: ~60%
- Neutral: ~25%

### Edge Cases
- Very angry customers
- Ambiguous requests
- Mixed sentiments
- Short/long texts

## Expected Results

With the default sample data, you should see:

### Good Model Performance
```
Intent Classification:
  Accuracy:          >85%
  F1-Score:          >0.80
  High Confidence:   >60%

Sentiment Analysis:
  Accuracy:          >90%
  F1-Score:          >0.85
  High Confidence:   >70%
```

### Areas to Watch
- **Low precision** on rare intents (fewer training samples)
- **Confusion** between similar intents (track_order vs report_delivery_delay)
- **Sentiment** easier than intent (fewer classes)

## Creating Your Own Test Set

### 1. From Labeled Data
```python
import pandas as pd

# Manual labeling
data = {
    'text': [
        "Where is my order?",
        "I want a refund",
        # ... more samples
    ],
    'intent_label': [
        "track_order",
        "request_refund",
        # ... corresponding labels
    ],
    'sentiment_label': [
        "neutral",
        "negative",
        # ... corresponding labels
    ]
}

df = pd.DataFrame(data)
df.to_csv('data/test_set.csv', index=False)
```

### 2. From Production Data
```python
from api.db.mongo import get_mongo_client, DATABASE_NAME

# Get real user messages
client = get_mongo_client()
db = client[DATABASE_NAME]
chats = db['chat_history']

# Sample messages
messages = list(chats.find({'from': 'user'}).limit(100))

# Manually label them
# ... export to CSV
```

### 3. Stratified Sampling
Ensure balanced representation:
- Equal samples per intent (~10-20 each)
- Equal samples per sentiment
- Mix of confidence levels
- Include edge cases

## Troubleshooting

### Low Accuracy
- **Check labels**: Are they correct?
- **Check distribution**: Too imbalanced?
- **Check text quality**: Typos, unclear language?
- **Retrain model**: May need more training data

### Low Confidence
- Model is uncertain
- May need more training data for those intents
- Text might be genuinely ambiguous

### High Accuracy but Low F1
- Class imbalance issue
- Model predicting majority class too often
- Use balanced accuracy instead

### Confusion Between Classes
- Check confusion matrix
- May need to combine similar intents
- Add more distinctive training examples

## Best Practices

### Test Set Size
- **Minimum**: 10 samples per class
- **Recommended**: 30-50 samples per class
- **Ideal**: 100+ samples per class

### Test Set Quality
- ✅ Real user messages
- ✅ Diverse phrasings
- ✅ Edge cases included
- ✅ Manually verified labels
- ❌ Don't use training data
- ❌ Don't synthetic/templated data only

### Regular Testing
- Test after any model changes
- Test with new production data monthly
- Compare metrics over time
- Track confidence trends

## Example: Full Workflow

```bash
# 1. Create test set from production data
python scripts/create_test_set.py --output data/prod_test_set.csv

# 2. Manually verify and label the data
# Edit data/prod_test_set.csv in Excel/Sheets

# 3. Run accuracy test
python scripts/test_nlu_accuracy.py --test-file data/prod_test_set.csv

# 4. Review results
cat results/nlu_metrics_*.json
open results/confusion_matrix_intent_*.png

# 5. If accuracy is low, analyze errors
python scripts/analyze_errors.py --predictions results/nlu_predictions_*.csv

# 6. Retrain if needed
jupyter notebook scripts/model_training.ipynb
```

## Advanced: Custom Metrics

To add custom metrics, modify the `calculate_metrics()` function:

```python
# Add ROC-AUC for sentiment (binary classification)
from sklearn.metrics import roc_auc_score

# For binary sentiment (positive vs negative)
if len(sentiment_labels) == 2:
    y_true_binary = [1 if s == 'positive' else 0 for s in y_true]
    y_pred_binary = [1 if s == 'positive' else 0 for s in y_pred]
    roc_auc = roc_auc_score(y_true_binary, y_pred_binary)
    metrics['roc_auc'] = roc_auc
```

## References

- [Scikit-learn Classification Metrics](https://scikit-learn.org/stable/modules/model_evaluation.html#classification-metrics)
- [Understanding Confusion Matrix](https://en.wikipedia.org/wiki/Confusion_matrix)
- [Precision vs Recall](https://en.wikipedia.org/wiki/Precision_and_recall)
- [F1 Score](https://en.wikipedia.org/wiki/F-score)

---

Happy Testing! 🧪📊
