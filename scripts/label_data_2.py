import pandas as pd
import csv
import re

# Define the input and output filenames
INPUT_CSV = './data/Bitext_Sample_Customer_Support_Training_cleaned.csv'
OUTPUT_CSV = './data/nlu_training_data_2.csv' # The second labeled data file

def get_intent_from_bitext(row):
    """
    Maps intents from the Bitext dataset to our project's intent labels.
    """
    category = str(row['category']).lower()
    intent = str(row['intent']).lower()
    
    # 1. Map all refund-related queries to our "order issue" intent
    if category == 'refund' or 'refund' in intent:
        return 'report_order_content_issue'
        
    # 2. Map order management queries (like 'cancel_order')
    if category == 'order' or 'order' in intent:
        return 'manage_order' # This will be a new intent
    
    # 3. Map payment queries
    if category == 'payment' or 'payment' in intent:
        return 'payment_issue' # This will be a new intent

    # 4. Fallback for everything else
    return 'generic_unspecified_feedback'

def create_labeled_dataset_from_bitext():
    """
    Main function to read the raw Bitext data, apply labels,
    and save the new dataset.
    """
    print(f"Starting labeling process for '{INPUT_CSV}'...")
    
    try:
        # The Bitext CSV seems to use a different encoding, try 'latin1'
        df = pd.read_csv(INPUT_CSV, encoding='latin1')
    except FileNotFoundError:
        print(f"Error: Input file '{INPUT_CSV}' not found.")
        return
    except Exception as e:
        print(f"An error occurred while reading the CSV: {e}")
        return

    labeled_data = []
    
    # Iterate over each row in the dataframe
    for index, row in df.iterrows():
        # 1. Get Text from 'instruction'
        text = row['instruction']
        
        # 2. Get Intent
        intent = get_intent_from_bitext(row)
        
        # 3. Get Sentiment (Default to 'neutral')
        sentiment = 'neutral'
        
        if not isinstance(text, str):
            text = ""

        # Clean the text (e.g., remove the {{Order Number}} placeholder)
        text = re.sub(r'\{\{.*?\}\}', '', text).strip()
        text = re.sub(r'\s+', ' ', text).strip()
        
        if text:
            labeled_data.append({
                'text': text,
                'intent': intent,
                'sentiment': sentiment
            })

    print(f"Processed {len(df)} rows.")
    print(f"Created {len(labeled_data)} labeled training examples.")
    
    # Save the new labeled data to a CSV file
    try:
        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['text', 'intent', 'sentiment'])
            writer.writeheader()
            writer.writerows(labeled_data)
        print(f"\nSuccessfully created labeled dataset: '{OUTPUT_CSV}'")
    except Exception as e:
        print(f"An error occurred while writing the new CSV: {e}")

if __name__ == "__main__":
    create_labeled_dataset_from_bitext()
