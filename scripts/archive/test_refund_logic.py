"""
Test script for the refund logic system.
This demonstrates the complete refund workflow:
1. Check refund eligibility (checks category and calculates amount)
2. Process refund (updates database)
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.mcp_client.client import (
    check_refund_eligibility_sync,
    process_refund_sync,
    query_order_sync
)
import json


def test_refund_eligibility():
    """Test refund eligibility check for different product categories."""
    
    print("\n" + "="*70)
    print("TESTING REFUND ELIGIBILITY LOGIC")
    print("="*70)
    
    # Test cases: [order_id, expected_eligible, description]
    test_cases = [
        ("ORD000001", True, "Fruits & Vegetables - Food item (NOT eligible)"),
        ("ORD000006", True, "Personal Care - Non-food item (ELIGIBLE)"),
        ("ORD000003", False, "Beverages - Food item (NOT eligible)"),
        ("ORD000038", False, "Snacks - Food item (NOT eligible)"),
        ("ORD000010", False, "Grocery - Food item (NOT eligible)"),
    ]
    
    for order_id, expected_eligible, description in test_cases:
        print(f"\n{'─'*70}")
        print(f"Test Case: {description}")
        print(f"Order ID: {order_id}")
        print(f"{'─'*70}")
        
        # First, query the order to see details
        order_details = query_order_sync(order_id)
        if "error" not in order_details:
            print(f"\nOrder Details:")
            print(f"  Product Category: {order_details.get('Product Category')}")
            print(f"  Order Value: ₹{order_details.get('Order Value (INR)')}")
        
        # Check refund eligibility
        result = check_refund_eligibility_sync(order_id)
        
        print(f"\nEligibility Check Result:")
        print(json.dumps(result, indent=2))
        
        # Verify result
        if result.get("eligible") == expected_eligible:
            print(f"\n✓ PASS: Eligibility matches expected ({expected_eligible})")
        else:
            print(f"\n✗ FAIL: Expected eligible={expected_eligible}, got {result.get('eligible')}")
    
    print(f"\n{'='*70}\n")


def test_refund_processing():
    """Test the complete refund workflow."""
    
    print("\n" + "="*70)
    print("TESTING REFUND PROCESSING WORKFLOW")
    print("="*70)
    
    # Use an eligible order (Personal Care)
    order_id = "ORD000032"
    
    print(f"\n{'─'*70}")
    print(f"Testing Complete Refund Workflow for {order_id}")
    print(f"{'─'*70}")
    
    # Step 1: Check eligibility
    print("\n[STEP 1] Checking refund eligibility...")
    eligibility = check_refund_eligibility_sync(order_id)
    print(json.dumps(eligibility, indent=2))
    
    if not eligibility.get("eligible"):
        print("\n✗ Order is not eligible for refund. Stopping test.")
        return
    
    # Step 2: Get refund amount
    refund_amount = eligibility.get("refund_amount")
    print(f"\n✓ Order is ELIGIBLE for refund")
    print(f"  Refund Amount: ₹{refund_amount}")
    
    # Step 3: Process the refund
    print(f"\n[STEP 2] Processing refund for ₹{refund_amount}...")
    refund_result = process_refund_sync(
        order_id=order_id,
        amount=refund_amount,
        reason="Test refund - customer request"
    )
    print(json.dumps(refund_result, indent=2))
    
    if refund_result.get("status") == "success":
        print(f"\n✓ Refund processed successfully!")
        print(f"  Transaction ID: {refund_result.get('transaction_id')}")
    else:
        print(f"\n✗ Refund processing failed: {refund_result.get('error')}")
    
    # Step 4: Verify the order is now marked as refunded
    print(f"\n[STEP 3] Verifying database update...")
    updated_order = query_order_sync(order_id)
    
    if updated_order.get("Refund Requested") == "Processed":
        print(f"✓ Order successfully marked as refunded in database")
        print(f"  Refund Amount: ₹{updated_order.get('Refund Amount')}")
        print(f"  Refund Reason: {updated_order.get('Refund Reason')}")
        print(f"  Refund Date: {updated_order.get('Refund Date')}")
    else:
        print(f"✗ Order not marked as refunded in database")
    
    print(f"\n{'='*70}\n")


def test_food_beverage_rejection():
    """Test that Food & Beverage items are correctly rejected."""
    
    print("\n" + "="*70)
    print("TESTING FOOD & BEVERAGE REJECTION")
    print("="*70)
    
    # Test with a beverage order
    order_id = "ORD000003"
    
    print(f"\n{'─'*70}")
    print(f"Testing Food & Beverage Rejection for {order_id}")
    print(f"{'─'*70}")
    
    # Check eligibility
    print("\n[STEP 1] Checking refund eligibility for Beverages...")
    eligibility = check_refund_eligibility_sync(order_id)
    print(json.dumps(eligibility, indent=2))
    
    if eligibility.get("eligible") == False:
        print(f"\n✓ PASS: Food & Beverage item correctly rejected")
        print(f"  Message to customer: {eligibility.get('message')}")
    else:
        print(f"\n✗ FAIL: Food & Beverage item should not be eligible")
    
    print(f"\n{'='*70}\n")


def test_duplicate_refund_prevention():
    """Test that already refunded orders cannot be refunded again."""
    
    print("\n" + "="*70)
    print("TESTING DUPLICATE REFUND PREVENTION")
    print("="*70)
    
    # Use the order we just refunded
    order_id = "ORD000032"
    
    print(f"\n{'─'*70}")
    print(f"Testing Duplicate Refund Prevention for {order_id}")
    print(f"{'─'*70}")
    
    # Check current status
    order_details = query_order_sync(order_id)
    print(f"\nCurrent Refund Status: {order_details.get('Refund Requested')}")
    
    # Try to process refund again
    print("\n[ATTEMPT] Trying to process refund again...")
    refund_result = process_refund_sync(
        order_id=order_id,
        amount=100,
        reason="Duplicate test"
    )
    print(json.dumps(refund_result, indent=2))
    
    if refund_result.get("status") == "failed" and "already been refunded" in refund_result.get("error", ""):
        print(f"\n✓ PASS: Duplicate refund correctly prevented")
    else:
        print(f"\n✗ FAIL: Duplicate refund should be prevented")
    
    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("REFUND LOGIC TEST SUITE")
    print("="*70)
    print("\nThis test suite demonstrates the complete refund workflow:")
    print("1. Check refund eligibility (Food & Beverage items cannot be refunded)")
    print("2. Calculate refund amount (order value - 5% shipping fee)")
    print("3. Process refund and update database")
    print("4. Prevent duplicate refunds")
    print("\n" + "="*70)
    
    try:
        # Test 1: Check eligibility for various product categories
        test_refund_eligibility()
        
        # Test 2: Complete refund workflow
        test_refund_processing()
        
        # Test 3: Food & Beverage rejection
        test_food_beverage_rejection()
        
        # Test 4: Duplicate refund prevention
        test_duplicate_refund_prevention()
        
        print("\n" + "="*70)
        print("ALL TESTS COMPLETED")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
