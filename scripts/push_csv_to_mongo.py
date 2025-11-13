"""
Script to push CSV data to MongoDB.
Each row in the CSV will be inserted as a document in MongoDB.
"""
import sys
import os
from pathlib import Path

# Add parent directory to path to import api modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from api.db.mongo import get_mongo_client, DATABASE_NAME
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
CSV_FILE_PATH = "data/Ecommerce_Delivery_Analytics_New.csv"
COLLECTION_NAME = "order_details"


def push_csv_to_mongo(csv_path: str, collection_name: str, batch_size: int = 1000):
    """
    Push CSV data to MongoDB.
    
    Args:
        csv_path: Path to the CSV file
        collection_name: Name of the MongoDB collection
        batch_size: Number of documents to insert at once
    
    Returns:
        bool: True if successful, False otherwise
    """
    client = None
    try:
        # Get MongoDB client
        logger.info("Connecting to MongoDB...")
        client = get_mongo_client()
        if client is None:
            logger.error("Failed to connect to MongoDB. Check your MONGO_URI environment variable.")
            return False
        
        # Get database and collection
        db = client[DATABASE_NAME]
        collection = db[collection_name]
        
        # Read CSV file
        logger.info(f"Reading CSV file: {csv_path}")
        df = pd.read_csv(csv_path)
        logger.info(f"Loaded {len(df)} rows from CSV")
        
        # Convert DataFrame to list of dictionaries
        # Each row becomes a document
        documents = df.to_dict('records')
        
        # Check if collection already has data
        existing_count = collection.count_documents({})
        if existing_count > 0:
            logger.warning(f"Collection '{collection_name}' already contains {existing_count} documents.")
            response = input("Do you want to (1) Clear and insert, (2) Append, or (3) Cancel? [1/2/3]: ")
            
            if response == "1":
                logger.info("Clearing existing documents...")
                collection.delete_many({})
                logger.info("Existing documents cleared.")
            elif response == "2":
                logger.info("Appending to existing documents...")
            else:
                logger.info("Operation cancelled.")
                return False
        
        # Insert documents in batches
        logger.info(f"Inserting {len(documents)} documents into collection '{collection_name}'...")
        total_inserted = 0
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            result = collection.insert_many(batch)
            total_inserted += len(result.inserted_ids)
            logger.info(f"Inserted {total_inserted}/{len(documents)} documents...")
        
        logger.info(f"✓ Successfully inserted {total_inserted} documents into MongoDB!")
        logger.info(f"  Database: {DATABASE_NAME}")
        logger.info(f"  Collection: {collection_name}")
        
        # Display some statistics
        logger.info("\nCollection Statistics:")
        logger.info(f"  Total documents: {collection.count_documents({})}")
        
        # Show a sample document
        sample_doc = collection.find_one()
        if sample_doc:
            logger.info("\nSample document structure:")
            for key in sample_doc.keys():
                if key != '_id':
                    logger.info(f"  - {key}")
        
        return True
        
    except FileNotFoundError:
        logger.error(f"CSV file not found: {csv_path}")
        return False
    except Exception as e:
        logger.exception(f"Error pushing data to MongoDB: {e}")
        return False
    finally:
        if client:
            client.close()
            logger.info("MongoDB connection closed.")


def main():
    """Main function to execute the script."""
    # Determine the CSV file path
    script_dir = Path(__file__).parent.parent
    csv_path = script_dir / CSV_FILE_PATH
    
    if not csv_path.exists():
        logger.error(f"CSV file not found at: {csv_path}")
        logger.info("Please check the CSV_FILE_PATH in the script.")
        return
    
    logger.info("=" * 60)
    logger.info("MongoDB CSV Import Script")
    logger.info("=" * 60)
    logger.info(f"CSV File: {csv_path}")
    logger.info(f"Collection: {COLLECTION_NAME}")
    logger.info("=" * 60)
    
    # Push data to MongoDB
    success = push_csv_to_mongo(str(csv_path), COLLECTION_NAME)
    
    if success:
        logger.info("\n✓ Data import completed successfully!")
    else:
        logger.error("\n✗ Data import failed.")


if __name__ == "__main__":
    main()
