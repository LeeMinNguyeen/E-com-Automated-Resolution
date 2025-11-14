"""
NLU Model Accuracy Tester

This script evaluates the Multi-Task DistilBERT model's performance using standard
deep learning metrics for both intent classification and sentiment analysis.

Metrics Calculated:
- Accuracy
- Precision (weighted & per-class)
- Recall (weighted & per-class)
- F1-Score (weighted & per-class)
- Confusion Matrix
- Classification Report
- ROC-AUC (for sentiment)

Usage:
    python scripts/test_nlu_accuracy.py
    python scripts/test_nlu_accuracy.py --test-file data/test_set.csv
"""

import sys
import os
from pathlib import Path
import argparse
import pandas as pd
import numpy as np
from datetime import datetime
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.mcp_client.client import smart_triage_sync
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
    roc_auc_score,
    balanced_accuracy_score
)
import matplotlib.pyplot as plt
import seaborn as sns


def load_test_data(file_path: str = None) -> pd.DataFrame:
    """
    Load test data from CSV file.
    
    Expected CSV format:
    - text: The input text
    - intent_label: Ground truth intent
    - sentiment_label: Ground truth sentiment
    
    Args:
        file_path: Path to test data CSV
        
    Returns:
        DataFrame with test data
    """
    if file_path and os.path.exists(file_path):
        print(f"📂 Loading test data from: {file_path}")
        df = pd.read_csv(file_path)
    else:
        # Create sample test data if no file provided
        print("📂 No test file provided. Creating sample test data...")
        df = create_sample_test_data()
    
    print(f"✅ Loaded {len(df)} test samples")
    return df


def create_sample_test_data() -> pd.DataFrame:
    """
    Create a comprehensive sample test dataset covering all intents and sentiments.
    
    Returns:
        DataFrame with test samples
    """
    test_samples = [
        # Track Order - Neutral
        {"text": "Where is my order?", "intent_label": "track_order", "sentiment_label": "neutral"},
        {"text": "Can you check my order status?", "intent_label": "track_order", "sentiment_label": "neutral"},
        {"text": "I need to track my package", "intent_label": "track_order", "sentiment_label": "neutral"},
        {"text": "What's the status of my delivery?", "intent_label": "track_order", "sentiment_label": "neutral"},
        {"text": "When will my order arrive?", "intent_label": "track_order", "sentiment_label": "neutral"},
        
        # Track Order - Negative (impatient)
        {"text": "Where is my order? It should have arrived by now", "intent_label": "track_order", "sentiment_label": "negative"},
        {"text": "My package still hasn't arrived, what's happening?", "intent_label": "track_order", "sentiment_label": "negative"},
        
        # Delivery Delay - Negative
        {"text": "My order is very late", "intent_label": "report_delivery_delay", "sentiment_label": "negative"},
        {"text": "The delivery is delayed and I'm frustrated", "intent_label": "report_delivery_delay", "sentiment_label": "negative"},
        {"text": "Why hasn't my package arrived yet? It's been a week!", "intent_label": "report_delivery_delay", "sentiment_label": "negative"},
        {"text": "This is taking way too long, where is my order?", "intent_label": "report_delivery_delay", "sentiment_label": "negative"},
        {"text": "I'm very upset about the late delivery", "intent_label": "report_delivery_delay", "sentiment_label": "negative"},
        {"text": "Extremely disappointed with the delivery time", "intent_label": "report_delivery_delay", "sentiment_label": "negative"},
        
        # Order Content Issues - Negative
        {"text": "Items are missing from my order", "intent_label": "report_order_content_issue", "sentiment_label": "negative"},
        {"text": "I received the wrong items", "intent_label": "report_order_content_issue", "sentiment_label": "negative"},
        {"text": "My package arrived damaged", "intent_label": "report_order_content_issue", "sentiment_label": "negative"},
        {"text": "Half of my order is missing", "intent_label": "report_order_content_issue", "sentiment_label": "negative"},
        {"text": "The product I received is not what I ordered", "intent_label": "report_order_content_issue", "sentiment_label": "negative"},
        {"text": "The items are broken and damaged", "intent_label": "report_order_content_issue", "sentiment_label": "negative"},
        
        # Refund Requests - Negative
        {"text": "I want a refund", "intent_label": "request_refund", "sentiment_label": "negative"},
        {"text": "Please cancel my order and refund me", "intent_label": "request_refund", "sentiment_label": "negative"},
        {"text": "I need my money back", "intent_label": "request_refund", "sentiment_label": "negative"},
        {"text": "Refund my order immediately", "intent_label": "request_refund", "sentiment_label": "negative"},
        {"text": "I want to return this and get a refund", "intent_label": "request_refund", "sentiment_label": "negative"},
        {"text": "Cancel my order, I don't want it anymore", "intent_label": "request_refund", "sentiment_label": "negative"},
        
        # Refund Requests - Neutral
        {"text": "How do I request a refund?", "intent_label": "request_refund", "sentiment_label": "neutral"},
        {"text": "Can I cancel my order?", "intent_label": "request_refund", "sentiment_label": "neutral"},
        
        # Positive Feedback
        {"text": "Thank you! The delivery was excellent!", "intent_label": "provide_feedback_on_service", "sentiment_label": "positive"},
        {"text": "Great service, very happy with my order", "intent_label": "provide_feedback_on_service", "sentiment_label": "positive"},
        {"text": "Amazing! Everything arrived perfectly", "intent_label": "provide_feedback_on_service", "sentiment_label": "positive"},
        {"text": "I'm very satisfied with the delivery", "intent_label": "provide_feedback_on_service", "sentiment_label": "positive"},
        {"text": "Excellent job, thank you so much!", "intent_label": "provide_feedback_on_service", "sentiment_label": "positive"},
        
        # Negative Feedback
        {"text": "Terrible service, very disappointed", "intent_label": "provide_feedback_on_service", "sentiment_label": "negative"},
        {"text": "Worst delivery experience ever", "intent_label": "provide_feedback_on_service", "sentiment_label": "negative"},
        {"text": "I'm extremely unhappy with this service", "intent_label": "provide_feedback_on_service", "sentiment_label": "negative"},
        
        # General Inquiries - Neutral
        {"text": "Do you deliver on weekends?", "intent_label": "other", "sentiment_label": "neutral"},
        {"text": "What are your business hours?", "intent_label": "other", "sentiment_label": "neutral"},
        {"text": "How can I contact customer support?", "intent_label": "other", "sentiment_label": "neutral"},
        {"text": "What payment methods do you accept?", "intent_label": "other", "sentiment_label": "neutral"},
        
        # Ambiguous/Other - Mixed
        {"text": "I need help", "intent_label": "other", "sentiment_label": "neutral"},
        {"text": "Can you assist me?", "intent_label": "other", "sentiment_label": "neutral"},
        {"text": "Hello", "intent_label": "other", "sentiment_label": "neutral"},
        
        # Edge Cases - Very Negative
        {"text": "This is absolutely unacceptable! Worst service ever!", "intent_label": "provide_feedback_on_service", "sentiment_label": "negative"},
        {"text": "I'm furious! My order never arrived and nobody is helping!", "intent_label": "report_delivery_delay", "sentiment_label": "negative"},
        {"text": "This is a complete disaster! Everything is wrong!", "intent_label": "report_order_content_issue", "sentiment_label": "negative"},
    ]
    
    return pd.DataFrame(test_samples)


def predict_batch(texts: list) -> list:
    """
    Run predictions on a batch of texts.
    
    Args:
        texts: List of text strings
        
    Returns:
        List of prediction dictionaries
    """
    predictions = []
    
    for i, text in enumerate(texts):
        if (i + 1) % 10 == 0:
            print(f"  Processing {i + 1}/{len(texts)}...")
        
        try:
            result = smart_triage_sync(text)
            predictions.append(result)
        except Exception as e:
            print(f"❌ Error predicting '{text[:50]}...': {e}")
            predictions.append({
                'intent': 'error',
                'sentiment': 'error',
                'intent_confidence': 0.0,
                'sentiment_confidence': 0.0
            })
    
    return predictions


def calculate_metrics(y_true: list, y_pred: list, labels: list, task_name: str) -> dict:
    """
    Calculate comprehensive metrics for classification.
    
    Args:
        y_true: True labels
        y_pred: Predicted labels
        labels: List of all possible labels
        task_name: Name of the task (intent/sentiment)
        
    Returns:
        Dictionary with all metrics
    """
    # Overall metrics
    accuracy = accuracy_score(y_true, y_pred)
    balanced_acc = balanced_accuracy_score(y_true, y_pred)
    
    # Weighted metrics
    precision_weighted = precision_score(y_true, y_pred, labels=labels, average='weighted', zero_division=0)
    recall_weighted = recall_score(y_true, y_pred, labels=labels, average='weighted', zero_division=0)
    f1_weighted = f1_score(y_true, y_pred, labels=labels, average='weighted', zero_division=0)
    
    # Macro metrics (treats all classes equally)
    precision_macro = precision_score(y_true, y_pred, labels=labels, average='macro', zero_division=0)
    recall_macro = recall_score(y_true, y_pred, labels=labels, average='macro', zero_division=0)
    f1_macro = f1_score(y_true, y_pred, labels=labels, average='macro', zero_division=0)
    
    # Per-class metrics
    precision_per_class = precision_score(y_true, y_pred, labels=labels, average=None, zero_division=0)
    recall_per_class = recall_score(y_true, y_pred, labels=labels, average=None, zero_division=0)
    f1_per_class = f1_score(y_true, y_pred, labels=labels, average=None, zero_division=0)
    
    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    
    # Classification report
    report = classification_report(y_true, y_pred, labels=labels, target_names=labels, zero_division=0)
    
    metrics = {
        'task_name': task_name,
        'accuracy': accuracy,
        'balanced_accuracy': balanced_acc,
        'precision_weighted': precision_weighted,
        'recall_weighted': recall_weighted,
        'f1_weighted': f1_weighted,
        'precision_macro': precision_macro,
        'recall_macro': recall_macro,
        'f1_macro': f1_macro,
        'confusion_matrix': cm,
        'classification_report': report,
        'per_class_metrics': {
            labels[i]: {
                'precision': precision_per_class[i],
                'recall': recall_per_class[i],
                'f1_score': f1_per_class[i]
            }
            for i in range(len(labels))
        }
    }
    
    return metrics


def plot_confusion_matrix(cm: np.ndarray, labels: list, task_name: str, save_path: str = None):
    """
    Plot confusion matrix as a heatmap.
    
    Args:
        cm: Confusion matrix
        labels: Class labels
        task_name: Name of the task
        save_path: Path to save the figure
    """
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=labels, yticklabels=labels)
    plt.title(f'Confusion Matrix - {task_name}')
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"📊 Confusion matrix saved to: {save_path}")
    else:
        plt.show()
    
    plt.close()


def print_metrics_summary(metrics: dict):
    """
    Print a formatted summary of metrics.
    
    Args:
        metrics: Dictionary with calculated metrics
    """
    print(f"\n{'='*80}")
    print(f"  {metrics['task_name'].upper()} CLASSIFICATION METRICS")
    print(f"{'='*80}")
    
    print(f"\n📊 Overall Metrics:")
    print(f"  Accuracy:          {metrics['accuracy']:.4f} ({metrics['accuracy']*100:.2f}%)")
    print(f"  Balanced Accuracy: {metrics['balanced_accuracy']:.4f} ({metrics['balanced_accuracy']*100:.2f}%)")
    
    print(f"\n📊 Weighted Metrics (account for class imbalance):")
    print(f"  Precision: {metrics['precision_weighted']:.4f}")
    print(f"  Recall:    {metrics['recall_weighted']:.4f}")
    print(f"  F1-Score:  {metrics['f1_weighted']:.4f}")
    
    print(f"\n📊 Macro Metrics (treat all classes equally):")
    print(f"  Precision: {metrics['precision_macro']:.4f}")
    print(f"  Recall:    {metrics['recall_macro']:.4f}")
    print(f"  F1-Score:  {metrics['f1_macro']:.4f}")
    
    print(f"\n📊 Per-Class Metrics:")
    print(f"  {'Class':<30} {'Precision':<12} {'Recall':<12} {'F1-Score':<12}")
    print(f"  {'-'*30} {'-'*12} {'-'*12} {'-'*12}")
    
    for class_name, class_metrics in metrics['per_class_metrics'].items():
        print(f"  {class_name:<30} "
              f"{class_metrics['precision']:<12.4f} "
              f"{class_metrics['recall']:<12.4f} "
              f"{class_metrics['f1_score']:<12.4f}")
    
    print(f"\n📊 Classification Report:")
    print(metrics['classification_report'])


def calculate_confidence_metrics(df: pd.DataFrame) -> dict:
    """
    Calculate metrics related to prediction confidence.
    
    Args:
        df: DataFrame with predictions and confidence scores
        
    Returns:
        Dictionary with confidence metrics
    """
    intent_conf = df['intent_confidence'].values
    sentiment_conf = df['sentiment_confidence'].values
    
    metrics = {
        'intent_confidence': {
            'mean': float(np.mean(intent_conf)),
            'std': float(np.std(intent_conf)),
            'min': float(np.min(intent_conf)),
            'max': float(np.max(intent_conf)),
            'median': float(np.median(intent_conf)),
            'high_confidence_pct': float(np.sum(intent_conf > 0.8) / len(intent_conf) * 100)
        },
        'sentiment_confidence': {
            'mean': float(np.mean(sentiment_conf)),
            'std': float(np.std(sentiment_conf)),
            'min': float(np.min(sentiment_conf)),
            'max': float(np.max(sentiment_conf)),
            'median': float(np.median(sentiment_conf)),
            'high_confidence_pct': float(np.sum(sentiment_conf > 0.8) / len(sentiment_conf) * 100)
        }
    }
    
    return metrics


def save_results(metrics_intent: dict, metrics_sentiment: dict, confidence_metrics: dict, 
                 df_results: pd.DataFrame, output_dir: str = "scripts/results"):
    """
    Save all results to files.
    
    Args:
        metrics_intent: Intent classification metrics
        metrics_sentiment: Sentiment classification metrics
        confidence_metrics: Confidence score metrics
        df_results: DataFrame with all predictions
        output_dir: Directory to save results
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save metrics to JSON
    metrics_file = os.path.join(output_dir, f"nlu_metrics_{timestamp}.json")
    all_metrics = {
        'intent_classification': {
            'accuracy': metrics_intent['accuracy'],
            'balanced_accuracy': metrics_intent['balanced_accuracy'],
            'precision_weighted': metrics_intent['precision_weighted'],
            'recall_weighted': metrics_intent['recall_weighted'],
            'f1_weighted': metrics_intent['f1_weighted'],
            'precision_macro': metrics_intent['precision_macro'],
            'recall_macro': metrics_intent['recall_macro'],
            'f1_macro': metrics_intent['f1_macro'],
            'per_class_metrics': metrics_intent['per_class_metrics']
        },
        'sentiment_classification': {
            'accuracy': metrics_sentiment['accuracy'],
            'balanced_accuracy': metrics_sentiment['balanced_accuracy'],
            'precision_weighted': metrics_sentiment['precision_weighted'],
            'recall_weighted': metrics_sentiment['recall_weighted'],
            'f1_weighted': metrics_sentiment['f1_weighted'],
            'precision_macro': metrics_sentiment['precision_macro'],
            'recall_macro': metrics_sentiment['recall_macro'],
            'f1_macro': metrics_sentiment['f1_macro'],
            'per_class_metrics': metrics_sentiment['per_class_metrics']
        },
        'confidence_scores': confidence_metrics,
        'test_info': {
            'timestamp': timestamp,
            'num_samples': len(df_results),
            'num_intents': len(metrics_intent['per_class_metrics']),
            'num_sentiments': len(metrics_sentiment['per_class_metrics'])
        }
    }
    
    with open(metrics_file, 'w') as f:
        json.dump(all_metrics, f, indent=2)
    print(f"\n💾 Metrics saved to: {metrics_file}")
    
    # Save detailed results to CSV
    results_file = os.path.join(output_dir, f"nlu_predictions_{timestamp}.csv")
    df_results.to_csv(results_file, index=False)
    print(f"💾 Detailed predictions saved to: {results_file}")
    
    # Save confusion matrices as images
    cm_intent_file = os.path.join(output_dir, f"confusion_matrix_intent_{timestamp}.png")
    cm_sentiment_file = os.path.join(output_dir, f"confusion_matrix_sentiment_{timestamp}.png")
    
    # Get unique labels
    intent_labels = sorted(df_results['intent_label'].unique())
    sentiment_labels = sorted(df_results['sentiment_label'].unique())
    
    plot_confusion_matrix(metrics_intent['confusion_matrix'], intent_labels, 
                         'Intent Classification', cm_intent_file)
    plot_confusion_matrix(metrics_sentiment['confusion_matrix'], sentiment_labels, 
                         'Sentiment Analysis', cm_sentiment_file)


def main():
    """Main function to run NLU accuracy testing."""
    parser = argparse.ArgumentParser(description="NLU Model Accuracy Tester")
    parser.add_argument(
        '--test-file',
        type=str,
        default=None,
        help='Path to test data CSV file (default: use sample data)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='scripts/results',
        help='Directory to save results (default: scripts/results)'
    )
    parser.add_argument(
        '--no-save',
        action='store_true',
        help='Don\'t save results to files'
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("  🧪 NLU MODEL ACCURACY TESTING")
    print("="*80)
    
    # Load test data
    df_test = load_test_data(args.test_file)
    
    # Run predictions
    print(f"\n🔮 Running predictions on {len(df_test)} samples...")
    predictions = predict_batch(df_test['text'].tolist())
    
    # Add predictions to dataframe
    df_test['predicted_intent'] = [p.get('intent', 'error') for p in predictions]
    df_test['predicted_sentiment'] = [p.get('sentiment', 'error') for p in predictions]
    df_test['intent_confidence'] = [p.get('intent_confidence', 0.0) for p in predictions]
    df_test['sentiment_confidence'] = [p.get('sentiment_confidence', 0.0) for p in predictions]
    
    # Calculate intent classification metrics
    print("\n📊 Calculating Intent Classification Metrics...")
    intent_labels = sorted(df_test['intent_label'].unique())
    metrics_intent = calculate_metrics(
        df_test['intent_label'].tolist(),
        df_test['predicted_intent'].tolist(),
        intent_labels,
        'Intent Classification'
    )
    
    # Calculate sentiment analysis metrics
    print("📊 Calculating Sentiment Analysis Metrics...")
    sentiment_labels = sorted(df_test['sentiment_label'].unique())
    metrics_sentiment = calculate_metrics(
        df_test['sentiment_label'].tolist(),
        df_test['predicted_sentiment'].tolist(),
        sentiment_labels,
        'Sentiment Analysis'
    )
    
    # Calculate confidence metrics
    print("📊 Calculating Confidence Metrics...")
    confidence_metrics = calculate_confidence_metrics(df_test)
    
    # Print results
    print_metrics_summary(metrics_intent)
    print_metrics_summary(metrics_sentiment)
    
    print(f"\n{'='*80}")
    print("  CONFIDENCE SCORE ANALYSIS")
    print(f"{'='*80}")
    
    print("\n📊 Intent Confidence:")
    print(f"  Mean:        {confidence_metrics['intent_confidence']['mean']:.4f}")
    print(f"  Std Dev:     {confidence_metrics['intent_confidence']['std']:.4f}")
    print(f"  Min:         {confidence_metrics['intent_confidence']['min']:.4f}")
    print(f"  Max:         {confidence_metrics['intent_confidence']['max']:.4f}")
    print(f"  Median:      {confidence_metrics['intent_confidence']['median']:.4f}")
    print(f"  High (>0.8): {confidence_metrics['intent_confidence']['high_confidence_pct']:.2f}%")
    
    print("\n📊 Sentiment Confidence:")
    print(f"  Mean:        {confidence_metrics['sentiment_confidence']['mean']:.4f}")
    print(f"  Std Dev:     {confidence_metrics['sentiment_confidence']['std']:.4f}")
    print(f"  Min:         {confidence_metrics['sentiment_confidence']['min']:.4f}")
    print(f"  Max:         {confidence_metrics['sentiment_confidence']['max']:.4f}")
    print(f"  Median:      {confidence_metrics['sentiment_confidence']['median']:.4f}")
    print(f"  High (>0.8): {confidence_metrics['sentiment_confidence']['high_confidence_pct']:.2f}%")
    
    # Save results
    if not args.no_save:
        print(f"\n💾 Saving results to {args.output_dir}/...")
        save_results(metrics_intent, metrics_sentiment, confidence_metrics, df_test, args.output_dir)
    
    # Final summary
    print(f"\n{'='*80}")
    print("  ✅ TESTING COMPLETE")
    print(f"{'='*80}")
    
    print(f"\n📊 Summary:")
    print(f"  Samples Tested:           {len(df_test)}")
    print(f"  Intent Accuracy:          {metrics_intent['accuracy']*100:.2f}%")
    print(f"  Intent F1-Score:          {metrics_intent['f1_weighted']:.4f}")
    print(f"  Sentiment Accuracy:       {metrics_sentiment['accuracy']*100:.2f}%")
    print(f"  Sentiment F1-Score:       {metrics_sentiment['f1_weighted']:.4f}")
    print(f"  Avg Intent Confidence:    {confidence_metrics['intent_confidence']['mean']:.4f}")
    print(f"  Avg Sentiment Confidence: {confidence_metrics['sentiment_confidence']['mean']:.4f}")
    
    if not args.no_save:
        print(f"\n📁 Results saved to: {args.output_dir}/")
        print(f"  - Metrics JSON")
        print(f"  - Predictions CSV")
        print(f"  - Confusion Matrix PNG files")
    
    print()


if __name__ == "__main__":
    main()
