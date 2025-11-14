"""
Database Analytics Module
Provides data retrieval functions for the dashboard
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import sys
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.db.mongo import get_mongo_client, DATABASE_NAME


def get_db_collections():
    """Get MongoDB collections"""
    try:
        client = get_mongo_client()
        if not client:
            logger.error("Failed to get MongoDB client")
            return None, None, None
        
        db = client[DATABASE_NAME]
        logger.debug(f"Connected to database: {DATABASE_NAME}")
        return (
            db['chat_history'],
            db['order_details'],
            db['human_intervention_alerts']
        )
    except Exception as e:
        logger.error(f"Error getting database collections: {e}", exc_info=True)
        return None, None, None


def get_chatbot_metrics(start_time: Optional[datetime] = None) -> Dict:
    """
    Get overall chatbot performance metrics
    
    Args:
        start_time: Start time for filtering (None for all time)
    
    Returns:
        Dictionary with metrics
    """
    logger.info(f"Fetching chatbot metrics from {start_time if start_time else 'all time'}")
    chats_col, orders_col, alerts_col = get_db_collections()
    if chats_col is None:
        logger.warning("No database connection, returning empty metrics")
        return _empty_metrics()
    
    try:
        # Build query filter
        query = {}
        if start_time:
            query['timestamp'] = {'$gte': start_time.timestamp()}
        
        # Get unique users
        users = chats_col.distinct('user_id', query)
        users_served = len(users)
        logger.info(f"Found {users_served} unique users")
        
        # Get users today
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        users_today = len(chats_col.distinct('user_id', {'timestamp': {'$gte': today_start.timestamp()}}))
        logger.debug(f"Users today: {users_today}")
        
        # Get conversations (count message pairs)
        total_messages = chats_col.count_documents(query)
        total_conversations = total_messages // 2  # Rough estimate
        logger.debug(f"Total messages: {total_messages}, conversations: {total_conversations}")
        
        # Calculate average response time (time between user message and bot response)
        pipeline = [
            {'$match': query},
            {'$sort': {'timestamp': 1}},
            {'$group': {
                '_id': '$user_id',
                'messages': {'$push': {'from': '$from', 'timestamp': '$timestamp'}}
            }}
        ]
        
        response_times = []
        for conv in chats_col.aggregate(pipeline):
            messages = conv['messages']
            for i in range(len(messages) - 1):
                if messages[i]['from'] == 'user' and messages[i + 1]['from'] == 'system':
                    response_time = messages[i + 1]['timestamp'] - messages[i]['timestamp']
                    if 0 < response_time < 60:  # Only count reasonable times
                        response_times.append(response_time)
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        logger.debug(f"Average response time: {avg_response_time:.2f}s from {len(response_times)} samples")
        
        # Get human intervention stats
        if alerts_col is not None:
            total_alerts = alerts_col.count_documents(query)
            pending_alerts = alerts_col.count_documents({**query, 'status': 'pending'})
            human_intervention_rate = (total_alerts / users_served * 100) if users_served > 0 else 0
            logger.info(f"Human intervention: {total_alerts} total, {pending_alerts} pending ({human_intervention_rate:.1f}%)")
        else:
            total_alerts = 0
            pending_alerts = 0
            human_intervention_rate = 0
        
        auto_resolution_rate = 100 - human_intervention_rate
        
        metrics = {
            'users_served': users_served,
            'users_today': users_today,
            'avg_response_time': avg_response_time,
            'human_intervention_rate': human_intervention_rate,
            'auto_resolution_rate': auto_resolution_rate,
            'total_conversations': total_conversations,
            'active_conversations': 0,  # Could be calculated based on recent activity
            'pending_alerts': pending_alerts
        }
        logger.info(f"Metrics calculated successfully: {users_served} users, {avg_response_time:.2f}s avg response")
        return metrics
        
    except Exception as e:
        logger.error(f"Error calculating chatbot metrics: {e}", exc_info=True)
        return _empty_metrics()


def get_intent_distribution(start_time: Optional[datetime] = None) -> pd.DataFrame:
    """
    Get distribution of customer intents
    
    Args:
        start_time: Start time for filtering
    
    Returns:
        DataFrame with intent counts
    """
    chats_col, _, _ = get_db_collections()
    if chats_col is None:
        return pd.DataFrame()
    
    # Get intents from NLU results (stored in conversation context or separate collection)
    # For now, we'll analyze this from a separate analytics collection or logs
    # This is a placeholder - you may want to store NLU results in a separate collection
    
    # Simulated data for demonstration
    intents = {
        'track_order': 45,
        'request_refund': 28,
        'report_delivery_delay': 15,
        'report_order_content_issue': 10,
        'provide_feedback_on_service': 2
    }
    
    return pd.DataFrame([
        {'intent': intent, 'count': count}
        for intent, count in intents.items()
    ])


def get_response_times(start_time: Optional[datetime] = None) -> pd.DataFrame:
    """
    Get response time trend data
    
    Args:
        start_time: Start time for filtering
    
    Returns:
        DataFrame with timestamp and response_time columns
    """
    chats_col, _, _ = get_db_collections()
    if chats_col is None:
        return pd.DataFrame()
    
    query = {}
    if start_time:
        query['timestamp'] = {'$gte': start_time.timestamp()}
    
    # Get message pairs and calculate response times
    pipeline = [
        {'$match': query},
        {'$sort': {'timestamp': 1}},
        {'$group': {
            '_id': '$user_id',
            'messages': {'$push': {'from': '$from', 'timestamp': '$timestamp'}}
        }}
    ]
    
    data = []
    for conv in chats_col.aggregate(pipeline):
        messages = conv['messages']
        for i in range(len(messages) - 1):
            if messages[i]['from'] == 'user' and messages[i + 1]['from'] == 'system':
                response_time = messages[i + 1]['timestamp'] - messages[i]['timestamp']
                if 0 < response_time < 60:
                    data.append({
                        'timestamp': datetime.fromtimestamp(messages[i + 1]['timestamp']),
                        'response_time': response_time
                    })
    
    return pd.DataFrame(data)


def get_refund_statistics(start_time: Optional[datetime] = None) -> Dict:
    """
    Get refund statistics
    
    Args:
        start_time: Start time for filtering
    
    Returns:
        Dictionary with refund stats
    """
    _, orders_col, _ = get_db_collections()
    if orders_col is None:
        return _empty_refund_stats()
    
    query = {'Refund Requested': 'Yes'}
    
    # Get refunded orders
    refunded_orders = list(orders_col.find(query))
    
    total_refunds = len(refunded_orders)
    total_amount = sum(order.get('Order Value (INR)', 0) for order in refunded_orders)
    items_refunded = total_refunds  # Each order is one item
    
    # Calculate refund rate
    total_orders = orders_col.count_documents({})
    refund_rate = (total_refunds / total_orders * 100) if total_orders > 0 else 0
    
    # Refunds by category
    category_refunds = {}
    for order in refunded_orders:
        category = order.get('Product Category', 'Unknown')
        if category not in category_refunds:
            category_refunds[category] = {'count': 0, 'amount': 0}
        category_refunds[category]['count'] += 1
        category_refunds[category]['amount'] += order.get('Order Value (INR)', 0)
    
    refund_by_category = pd.DataFrame([
        {
            'category': cat,
            'count': data['count'],
            'total_amount': data['amount']
        }
        for cat, data in category_refunds.items()
    ])
    
    # Refund reasons (based on customer feedback)
    reasons = {}
    for order in refunded_orders:
        feedback = order.get('Customer Feedback', '')
        if 'missing' in feedback.lower():
            reason = 'Items Missing'
        elif 'late' in feedback.lower() or 'delay' in feedback.lower():
            reason = 'Late Delivery'
        elif 'damaged' in feedback.lower():
            reason = 'Damaged Items'
        else:
            reason = 'Other'
        
        reasons[reason] = reasons.get(reason, 0) + 1
    
    refund_reasons = pd.DataFrame([
        {'reason': reason, 'count': count}
        for reason, count in reasons.items()
    ])
    
    return {
        'total_refunds': total_refunds,
        'total_amount': total_amount,
        'items_refunded': items_refunded,
        'refund_rate': refund_rate,
        'refund_by_category': refund_by_category,
        'refund_reasons': refund_reasons
    }


def get_service_ratings(start_time: Optional[datetime] = None) -> Dict:
    """
    Get service rating statistics
    
    Args:
        start_time: Start time for filtering
    
    Returns:
        Dictionary with rating stats
    """
    _, orders_col, _ = get_db_collections()
    if orders_col is None:
        return _empty_rating_stats()
    
    # Get all orders with ratings
    orders = list(orders_col.find({}, {'Service Rating': 1}))
    
    ratings = [order.get('Service Rating', 0) for order in orders if order.get('Service Rating')]
    
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    total_ratings = len(ratings)
    
    # Rating distribution
    rating_counts = {}
    for rating in ratings:
        rating_counts[rating] = rating_counts.get(rating, 0) + 1
    
    rating_distribution = pd.DataFrame([
        {'rating': rating, 'count': count}
        for rating, count in sorted(rating_counts.items())
    ])
    
    return {
        'avg_rating': avg_rating,
        'total_ratings': total_ratings,
        'rating_distribution': rating_distribution
    }


def get_human_intervention_alerts() -> pd.DataFrame:
    """
    Get human intervention alerts
    
    Returns:
        DataFrame with alerts
    """
    logger.info("Fetching human intervention alerts")
    _, _, alerts_col = get_db_collections()
    if alerts_col is None:
        logger.warning("No database connection for alerts")
        return pd.DataFrame()
    
    try:
        # Get all alerts
        alerts = list(alerts_col.find().sort('timestamp', -1))
        logger.info(f"Found {len(alerts)} alerts in database")
        
        data = []
        for alert in alerts:
            data.append({
                'alert_id': str(alert['_id']),
                'user_id': alert.get('user_id', 'unknown'),
                'reason': alert.get('reason', 'Unknown'),
                'last_message': alert.get('last_message', ''),
                'timestamp': datetime.fromtimestamp(alert.get('timestamp', datetime.now().timestamp())),
                'status': alert.get('status', 'pending'),
                'priority': alert.get('priority', 'medium')
            })
        
        logger.debug(f"Processed {len(data)} alerts")
        return pd.DataFrame(data)
        
    except Exception as e:
        logger.error(f"Error fetching human intervention alerts: {e}", exc_info=True)
        return pd.DataFrame()


def mark_alert_resolved(alert_id: str):
    """
    Mark an alert as resolved
    
    Args:
        alert_id: Alert ID to resolve
    """
    from bson import ObjectId
    
    logger.info(f"Marking alert {alert_id} as resolved")
    _, _, alerts_col = get_db_collections()
    if alerts_col is None:
        logger.error("No database connection to mark alert resolved")
        return
    
    try:
        result = alerts_col.update_one(
            {'_id': ObjectId(alert_id)},
            {'$set': {
                'status': 'resolved',
                'resolved_at': datetime.now().timestamp()
            }}
        )
        if result.modified_count > 0:
            logger.info(f"Alert {alert_id} successfully marked as resolved")
        else:
            logger.warning(f"Alert {alert_id} not found or already resolved")
    except Exception as e:
        logger.error(f"Error marking alert {alert_id} as resolved: {e}", exc_info=True)


def get_recent_conversations(limit: int = 20, user_id: Optional[str] = None) -> pd.DataFrame:
    """
    Get recent conversations
    
    Args:
        limit: Number of messages to retrieve
        user_id: Filter by specific user
    
    Returns:
        DataFrame with conversation history
    """
    chats_col, _, _ = get_db_collections()
    if chats_col is None:
        return pd.DataFrame()
    
    query = {}
    if user_id:
        query['user_id'] = user_id
    
    # Get recent messages
    messages = list(chats_col.find(query).sort('timestamp', -1).limit(limit))
    
    data = []
    for msg in messages:
        # Handle timestamp - it should be a Unix timestamp (number)
        timestamp_value = msg.get('timestamp')
        if timestamp_value:
            try:
                if isinstance(timestamp_value, (int, float)):
                    timestamp = datetime.fromtimestamp(timestamp_value)
                elif isinstance(timestamp_value, datetime):
                    # Remove timezone info to make it naive
                    timestamp = timestamp_value.replace(tzinfo=None) if timestamp_value.tzinfo else timestamp_value
                else:
                    # Try to parse if it's a string
                    parsed = datetime.fromisoformat(str(timestamp_value).replace('Z', '+00:00'))
                    # Make it naive
                    timestamp = parsed.replace(tzinfo=None)
            except (ValueError, OSError):
                timestamp = datetime.now()
        else:
            timestamp = datetime.now()
        
        data.append({
            'user_id': msg.get('user_id', 'unknown'),
            'from': msg.get('from', 'unknown'),
            'to': msg.get('to', 'unknown'),
            'text': msg.get('text', ''),
            'timestamp': timestamp
        })
    
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values('timestamp')
    
    return df


def get_order_analytics(start_time: Optional[datetime] = None) -> Dict:
    """
    Get order analytics
    
    Args:
        start_time: Start time for filtering
    
    Returns:
        Dictionary with order stats
    """
    _, orders_col, _ = get_db_collections()
    if orders_col is None:
        return _empty_order_stats()
    
    # Get all orders
    orders = list(orders_col.find({}))
    
    total_orders = len(orders)
    
    # Delayed deliveries
    delayed = [o for o in orders if o.get('Delivery Delay') == 'Yes']
    delayed_deliveries = len(delayed)
    delay_rate = (delayed_deliveries / total_orders * 100) if total_orders > 0 else 0
    
    # Average delivery time
    delivery_times = [o.get('Delivery Time (Minutes)', 0) for o in orders if o.get('Delivery Time (Minutes)')]
    avg_delivery_time = sum(delivery_times) / len(delivery_times) if delivery_times else 0
    
    # Average order value
    order_values = [o.get('Order Value (INR)', 0) for o in orders if o.get('Order Value (INR)')]
    avg_order_value = sum(order_values) / len(order_values) if order_values else 0
    
    # Platform distribution
    platforms = {}
    for order in orders:
        platform = order.get('Platform', 'Unknown')
        platforms[platform] = platforms.get(platform, 0) + 1
    
    platform_distribution = pd.DataFrame([
        {'platform': platform, 'count': count}
        for platform, count in platforms.items()
    ])
    
    # Category distribution
    categories = {}
    for order in orders:
        category = order.get('Product Category', 'Unknown')
        categories[category] = categories.get(category, 0) + 1
    
    category_distribution = pd.DataFrame([
        {'category': category, 'count': count}
        for category, count in categories.items()
    ])
    
    return {
        'total_orders': total_orders,
        'delayed_deliveries': delayed_deliveries,
        'delay_rate': delay_rate,
        'avg_delivery_time': avg_delivery_time,
        'avg_order_value': avg_order_value,
        'platform_distribution': platform_distribution,
        'category_distribution': category_distribution
    }


def _empty_metrics() -> Dict:
    """Return empty metrics structure"""
    return {
        'users_served': 0,
        'users_today': 0,
        'avg_response_time': 0,
        'human_intervention_rate': 0,
        'auto_resolution_rate': 100,
        'pending_alerts': 0,
        'total_conversations': 0,
        'active_conversations': 0
    }


def _empty_refund_stats() -> Dict:
    """Return empty refund stats"""
    return {
        'total_refunds': 0,
        'total_amount': 0,
        'items_refunded': 0,
        'refund_rate': 0,
        'refund_by_category': pd.DataFrame(),
        'refund_reasons': pd.DataFrame()
    }


def _empty_rating_stats() -> Dict:
    """Return empty rating stats"""
    return {
        'avg_rating': 0,
        'total_ratings': 0,
        'rating_distribution': pd.DataFrame()
    }


def _empty_order_stats() -> Dict:
    """Return empty order stats"""
    return {
        'total_orders': 0,
        'delayed_deliveries': 0,
        'delay_rate': 0,
        'avg_delivery_time': 0,
        'avg_order_value': 0,
        'platform_distribution': pd.DataFrame(),
        'category_distribution': pd.DataFrame()
    }
