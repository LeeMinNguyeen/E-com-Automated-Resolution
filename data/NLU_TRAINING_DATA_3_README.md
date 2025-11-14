# NLU Training Data 3 - Customer Service Intents

## Overview
This file supplements the existing training data (`nlu_training_data.csv` and `nlu_training_data_2.csv`) with **customer service-specific intents** that were missing from the original datasets.

## Problem Identified
The model had **11.11% intent accuracy** because of a severe label mismatch:
- **Training data** contained: feedback, reviews, product quality comments
- **Test data** expected: order tracking, refunds, delivery delays, customer service actions

## Solution
Created 500+ training samples covering the missing intents that match real customer service scenarios.

## New Intents Added

### 1. `track_order` (70+ samples)
Customer wants to know the status or location of their order.

**Examples:**
- "Where is my order?"
- "Can you check my order status?"
- "I need to track my package"
- "Track my order ORD123456"
- "What's my tracking number?"

**Sentiments:**
- Neutral (most cases - simple inquiry)
- Negative (impatient/worried customers)

### 2. `report_delivery_delay` (80+ samples)
Customer reporting that their order is late or overdue.

**Examples:**
- "My order is very late"
- "The delivery is delayed and I'm frustrated"
- "Why hasn't my package arrived yet? It's been a week!"
- "Order is 10 days late"
- "Package stuck in transit"

**Sentiments:**
- Negative (frustration, disappointment)

### 3. `request_refund` (60+ samples)
Customer wants to cancel order and get money back.

**Examples:**
- "I want a refund"
- "Please cancel my order and refund me"
- "I need my money back"
- "How do I request a refund?" (neutral inquiry)
- "What's your refund policy?"

**Sentiments:**
- Negative (demanding refund)
- Neutral (asking about process)

### 4. `other` (150+ samples)
General inquiries, greetings, or requests that don't fit other categories.

**Categories included:**
- Greetings: "Hello", "Hi there", "Good morning"
- General help: "I need help", "Can you assist me?"
- Human escalation: "I want to speak to a human", "Connect me to an agent"
- Business info: "What are your business hours?", "Do you deliver on weekends?"
- Shipping inquiries: "Do you ship internationally?", "Shipping cost?"
- Payment questions: "What payment methods do you accept?", "Can I pay with PayPal?"
- Product info: "Is this in stock?", "Product details?"
- Policy questions: "Warranty information?", "Return policy?"
- Acknowledgements: "Thanks", "Got it", "Understood"

**Sentiments:**
- Neutral (informational queries)

### 5. Enhanced Existing Intents

#### `report_order_content_issue` (100+ samples)
Added more specific scenarios:
- Missing items: "Items missing from my order", "Half of my order is missing"
- Wrong items: "I received the wrong items", "Wrong product sent"
- Damaged items: "My package arrived damaged", "Package contents are broken"
- Quality issues: "Item is defective", "Product won't turn on"
- Tampering: "Package was tampered with", "Box was opened"
- Expiry: "Item is expired", "Product is past expiry date"
- Variant errors: "Ordered blue but got red", "Wrong size sent"

#### `provide_feedback_on_service` (100+ samples)
Enhanced with specific aspects:
- Positive delivery: "Fast delivery loved it", "Arrived early thanks!"
- Negative delivery: "Terrible service very disappointed"
- Delivery person: "Delivery guy was very polite" / "Rude delivery person"
- Packaging: "Great packaging" / "Poor packaging"
- Overall satisfaction: "Will order again" / "Never buying again"

## Dataset Statistics

| Intent | Sample Count | Sentiment Distribution |
|--------|-------------|------------------------|
| `track_order` | 70 | Neutral: 60%, Negative: 40% |
| `report_delivery_delay` | 80 | Negative: 100% |
| `request_refund` | 60 | Negative: 70%, Neutral: 30% |
| `other` | 150 | Neutral: 100% |
| `report_order_content_issue` | 100 | Negative: 100% |
| `provide_feedback_on_service` | 100 | Positive: 45%, Negative: 45%, Neutral: 10% |
| **TOTAL** | **560** | Balanced across all categories |

## Integration with Existing Data

### Combined Dataset:
- `nlu_training_data.csv`: ~100,000 samples (generic feedback, product quality)
- `nlu_training_data_2.csv`: Additional samples
- `nlu_training_data_3.csv`: **560 samples** (customer service intents)

### Training Impact:
The model will now learn:
1. **Generic e-commerce feedback** (from data 1 & 2)
2. **Customer service actions** (from data 3)

This creates a **comprehensive model** that can handle both feedback analysis and actionable customer service requests.

## Usage in Google Colab

### Option 1: Manual Upload
```python
# Upload the file to Colab
from google.colab import files
uploaded = files.upload()
# Select nlu_training_data_3.csv from your computer

TRAINING_FILES = [
    'nlu_training_data.csv',
    'nlu_training_data_2.csv', 
    'nlu_training_data_3.csv'
]
```

### Option 2: Google Drive
1. Upload `nlu_training_data_3.csv` to Google Drive
2. Get shareable link
3. Use gdown in notebook:
```python
url3 = "https://drive.google.com/uc?id=YOUR_FILE_ID"
gdown.download(url3, "/content/nlu_training_data_3.csv")
```

### Option 3: Direct from GitHub
If this file is in your repository:
```python
!wget https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/data/nlu_training_data_3.csv
```

## Expected Accuracy Improvement

### Before (with only data 1 & 2):
- Intent Accuracy: **11.11%**
- Intent F1-Score: **0.1101**
- Problem: Model never learned customer service intents

### After (with all 3 files):
- Expected Intent Accuracy: **80-90%+**
- Expected Intent F1-Score: **0.80-0.90+**
- Model will recognize all 6 intent categories

## Label Mapping

The model will now have these intents:

| Intent Label | Source | Purpose |
|--------------|--------|---------|
| `track_order` | Data 3 | Order status inquiries |
| `report_delivery_delay` | Data 3 | Late delivery complaints |
| `request_refund` | Data 3 | Refund/cancellation requests |
| `other` | Data 3 | General inquiries, greetings |
| `report_order_content_issue` | All 3 | Wrong/missing/damaged items |
| `provide_feedback_on_service` | All 3 | Service feedback (positive/negative) |
| `generic_unspecified_feedback` | Data 1 & 2 | General feedback |
| `comment_on_platform_experience` | Data 1 & 2 | Platform/app feedback |
| `comment_on_product_quality` | Data 1 & 2 | Product quality comments |
| `manage_order` | Data 1 & 2 | Order management |

## Next Steps

1. **Upload** `nlu_training_data_3.csv` to Google Colab
2. **Update** the notebook cell to include all 3 files (already done ✅)
3. **Retrain** the model with combined dataset
4. **Re-run** `test_nlu_accuracy.py` to verify improved metrics
5. **Save** the new model to replace the current one

## File Location
- Local: `e:\Project\E-com-Automated-Resolution\data\nlu_training_data_3.csv`
- Format: CSV with columns: `text`, `intent`, `sentiment`
- Encoding: UTF-8
- Total rows: 561 (including header)
