"""
Customer Support Dashboard - E-commerce Chatbot Monitoring
Real-time dashboard for monitoring chatbot performance and analytics
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dashboard/dashboard.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dashboard.db_analytics import (
    get_chatbot_metrics,
    get_intent_distribution,
    get_response_times,
    get_refund_statistics,
    get_service_ratings,
    get_human_intervention_alerts,
    get_recent_conversations,
    get_order_analytics,
    mark_alert_resolved
)

# Page configuration
st.set_page_config(
    page_title="Customer Support Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .alert-card {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ff6b6b;
        margin-bottom: 1rem;
    }
    .resolved-card {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #28a745;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

def main():
    """Main dashboard application"""
    logger.info("Dashboard application started")
    
    # Header
    st.markdown('<p class="main-header">📊 Customer Support Dashboard</p>', unsafe_allow_html=True)
    
    # Sidebar - Filters and Refresh
    with st.sidebar:
        st.header("⚙️ Dashboard Controls")
        
        # Time range filter
        time_range = st.selectbox(
            "Time Range",
            ["Last Hour", "Last 24 Hours", "Last 7 Days", "Last 30 Days", "All Time"],
            index=1
        )
        logger.info(f"Time range selected: {time_range}")
        
        # Auto-refresh toggle
        auto_refresh = st.checkbox("Auto-refresh (30s)", value=True)
        if auto_refresh:
            logger.debug("Auto-refresh enabled")
            
        # Manual refresh button
        if st.button("🔄 Refresh Now", width='stretch'):
            logger.info("Manual refresh triggered")
            st.rerun()
        
        st.divider()
    
    # Calculate time range
    now = datetime.now()
    if time_range == "Last Hour":
        start_time = now - timedelta(hours=1)
    elif time_range == "Last 24 Hours":
        start_time = now - timedelta(hours=24)
    elif time_range == "Last 7 Days":
        start_time = now - timedelta(days=7)
    elif time_range == "Last 30 Days":
        start_time = now - timedelta(days=30)
    else:
        start_time = None
    
    logger.info(f"Fetching data from: {start_time if start_time else 'All time'}")
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "🎯 Overview", 
        "🚨 Alerts", 
        "📈 Analytics", 
        "💬 Conversations"
    ])
    
    # ==================== TAB 1: OVERVIEW ====================
    with tab1:
        logger.info("Rendering Overview tab")
        st.header("Performance Overview")
        
        # Get metrics
        try:
            metrics = get_chatbot_metrics(start_time)
            logger.info(f"Metrics fetched: {metrics['users_served']} users served")
        except Exception as e:
            logger.error(f"Error fetching chatbot metrics: {e}", exc_info=True)
            st.error(f"Failed to load metrics: {e}")
            return
        
        # Key Metrics Row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="👥 Users Served",
                value=metrics['users_served'],
                delta=f"+{metrics.get('users_today', 0)} today"
            )
        
        with col2:
            avg_response = metrics['avg_response_time']
            st.metric(
                label="⚡ Avg Response Time",
                value=f"{avg_response:.2f}s",
                delta="Good" if avg_response < 3 else "Slow",
                delta_color="normal" if avg_response < 3 else "inverse"
            )
        
        with col3:
            human_rate = metrics['human_intervention_rate']
            st.metric(
                label="🤝 Human Intervention",
                value=f"{human_rate:.1f}%",
                delta=f"{metrics['pending_alerts']} pending"
            )
        
        with col4:
            resolution_rate = metrics['auto_resolution_rate']
            st.metric(
                label="✅ Auto-Resolution Rate",
                value=f"{resolution_rate:.1f}%",
                delta="Excellent" if resolution_rate > 80 else "Good"
            )
        
        st.divider()
        
        # Second Row of Metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            try:
                refund_stats = get_refund_statistics(start_time)
                logger.info(f"Refund stats fetched: {refund_stats['total_refunds']} refunds")
                st.metric(
                    label="💰 Refunds Processed",
                    value=refund_stats['total_refunds'],
                    delta=f"₹{refund_stats['total_amount']:,.0f}"
                )
            except Exception as e:
                logger.error(f"Error fetching refund statistics: {e}", exc_info=True)
                st.error("Failed to load refund stats")
        
        with col2:
            st.metric(
                label="📦 Items Refunded",
                value=refund_stats['items_refunded'],
                delta=f"{refund_stats['refund_rate']:.1f}% of orders"
            )
        
        with col3:
            try:
                rating_stats = get_service_ratings(start_time)
                logger.info(f"Rating stats fetched: {rating_stats['avg_rating']:.2f} avg rating")
                st.metric(
                    label="⭐ Avg Service Rating",
                    value=f"{rating_stats['avg_rating']:.2f}/5",
                    delta=f"{rating_stats['total_ratings']} ratings"
                )
            except Exception as e:
                logger.error(f"Error fetching service ratings: {e}", exc_info=True)
                st.error("Failed to load ratings")
        
        with col4:
            st.metric(
                label="📊 Total Conversations",
                value=metrics['total_conversations'],
                delta=f"{metrics.get('active_conversations', 0)} active"
            )
        
        st.divider()
        
        # Charts Row
        col1, col2 = st.columns(2)
        
        with col1:
            # Intent Distribution
            st.subheader("🎯 Intent Distribution")
            try:
                intent_data = get_intent_distribution(start_time)
                logger.info(f"Intent distribution fetched: {len(intent_data)} intents")
                
                if not intent_data.empty:
                    fig = px.pie(
                        intent_data,
                        values='count',
                        names='intent',
                        title='Customer Request Types',
                        hole=0.4
                    )
                    fig.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig, width='stretch')
                else:
                    st.info("No intent data available for the selected time range")
            except Exception as e:
                logger.error(f"Error rendering intent distribution: {e}", exc_info=True)
                st.error("Failed to load intent distribution")
        
        with col2:
            # Service Ratings Distribution
            st.subheader("⭐ Service Ratings")
            try:
                if not rating_stats['rating_distribution'].empty:
                    fig = px.bar(
                        rating_stats['rating_distribution'],
                        x='rating',
                        y='count',
                        title='Rating Distribution',
                        labels={'rating': 'Rating', 'count': 'Number of Orders'},
                        color='rating',
                        color_continuous_scale='RdYlGn'
                    )
                    st.plotly_chart(fig, width='stretch')
                else:
                    st.info("No rating data available")
            except Exception as e:
                logger.error(f"Error rendering service ratings chart: {e}", exc_info=True)
                st.error("Failed to load service ratings chart")
        
        # Response Time Trend
        st.subheader("⚡ Response Time Trend")
        try:
            response_time_data = get_response_times(start_time)
            logger.info(f"Response time data fetched: {len(response_time_data)} data points")
            
            if not response_time_data.empty:
                fig = px.line(
                response_time_data,
                x='timestamp',
                y='response_time',
                title='Response Time Over Time',
                labels={'response_time': 'Response Time (seconds)', 'timestamp': 'Time'}
                )
                fig.add_hline(y=3, line_dash="dash", line_color="red", annotation_text="Target: 3s")

                # Compute a fixed y-axis range (with small padding) so y-axis doesn't auto-rescale when zooming on x
                y_vals = response_time_data['response_time'].dropna()
                if not y_vals.empty:
                    ymin = float(y_vals.min())
                    ymax = float(y_vals.max())
                    if ymin == ymax:
                        # ensure a non-zero range for constant series
                        ymin -= 1.0
                        ymax += 1.0
                    pad = (ymax - ymin) * 0.1
                    ymin -= pad
                    ymax += pad
                else:
                    ymin, ymax = 0.0, 5.0

                # Disable autorange and set the static range for the y-axis
                fig.update_yaxes(autorange=False, range=[ymin, ymax])
                # Optionally prevent any y-axis zoom/pan interactions by uncommenting:
                # fig.update_yaxes(fixedrange=True)

                st.plotly_chart(fig, width='stretch')
            else:
                st.info("No response time data available")
        except Exception as e:
            logger.error(f"Error rendering response time trend: {e}", exc_info=True)
            st.error("Failed to load response time trend")
    
    # ==================== TAB 2: ALERTS ====================
    with tab2:
        logger.info("Rendering Alerts tab")
        st.header("🚨 Human Intervention Alerts")
        
        # Get alerts
        try:
            alerts = get_human_intervention_alerts()
            logger.info(f"Alerts fetched: {len(alerts)} total alerts")
        except Exception as e:
            logger.error(f"Error fetching human intervention alerts: {e}", exc_info=True)
            st.error(f"Failed to load alerts: {e}")
            return
        
        if alerts.empty:
            logger.info("No alerts found")
            st.success("✅ No pending alerts! All conversations are being handled automatically.")
        else:
            # Filter buttons
            col1, col2, col3 = st.columns(3)
            with col1:
                show_pending = st.checkbox("Show Pending", value=True)
            with col2:
                show_resolved = st.checkbox("Show Resolved", value=False)
            with col3:
                st.metric("Pending Alerts", len(alerts[alerts['status'] == 'pending']))
            
            st.divider()
            
            # Display alerts
            for idx, alert in alerts.iterrows():
                if alert['status'] == 'pending' and not show_pending:
                    continue
                if alert['status'] == 'resolved' and not show_resolved:
                    continue
                
                # Alert card
                card_class = "alert-card" if alert['status'] == 'pending' else "resolved-card"
                
                with st.container():
                    st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
                    
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        st.markdown(f"**User ID:** `{alert['user_id']}`")
                        st.markdown(f"**Reason:** {alert['reason']}")
                        st.markdown(f"**Message:** _{alert['last_message']}_")
                    
                    with col2:
                        st.markdown(f"**Time:** {alert['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
                        st.markdown(f"**Status:** {'🔴 Pending' if alert['status'] == 'pending' else '✅ Resolved'}")
                        if alert['priority']:
                            st.markdown(f"**Priority:** {alert['priority']}")
                    
                    with col3:
                        if alert['status'] == 'pending':
                            if st.button("✅ Resolve", key=f"resolve_{idx}"):
                                logger.info(f"Resolving alert: {alert['alert_id']}")
                                try:
                                    mark_alert_resolved(alert['alert_id'])
                                    logger.info(f"Alert {alert['alert_id']} marked as resolved")
                                    st.success("Alert marked as resolved!")
                                    st.rerun()
                                except Exception as e:
                                    logger.error(f"Error resolving alert {alert['alert_id']}: {e}", exc_info=True)
                                    st.error(f"Failed to resolve alert: {e}")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
    
    # ==================== TAB 3: ANALYTICS ====================
    with tab3:
        logger.info("Rendering Analytics tab")
        st.header("📈 Detailed Analytics")
        
        # Order Analytics
        st.subheader("📦 Order & Delivery Analytics")
        try:
            order_stats = get_order_analytics(start_time)
            logger.info(f"Order analytics fetched: {order_stats['total_orders']} orders")
        except Exception as e:
            logger.error(f"Error fetching order analytics: {e}", exc_info=True)
            st.error(f"Failed to load order analytics: {e}")
            return
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Orders", order_stats['total_orders'])
        with col2:
            st.metric("Delayed Deliveries", 
                     order_stats['delayed_deliveries'],
                     delta=f"{order_stats['delay_rate']:.1f}%")
        with col3:
            st.metric("Avg Delivery Time", 
                     f"{order_stats['avg_delivery_time']:.0f} min")
        with col4:
            st.metric("Avg Order Value", 
                     f"₹{order_stats['avg_order_value']:.2f}")
        
        st.divider()
        
        # Platform Distribution
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🏪 Orders by Platform")
            if not order_stats['platform_distribution'].empty:
                fig = px.bar(
                    order_stats['platform_distribution'],
                    x='platform',
                    y='count',
                    title='Orders by Platform',
                    color='count',
                    color_continuous_scale='Viridis'
                )
                st.plotly_chart(fig, width='stretch')
        
        with col2:
            st.subheader("📦 Product Categories")
            if not order_stats['category_distribution'].empty:
                fig = px.pie(
                    order_stats['category_distribution'],
                    values='count',
                    names='category',
                    title='Orders by Category'
                )
                st.plotly_chart(fig, width='stretch')
        
        # Refund Analysis
        st.subheader("💰 Refund Analysis")
        refund_stats = get_refund_statistics(start_time)
        
        col1, col2 = st.columns(2)
        with col1:
            if not refund_stats['refund_by_category'].empty:
                fig = px.bar(
                    refund_stats['refund_by_category'],
                    x='category',
                    y='total_amount',
                    title='Refund Amount by Category',
                    labels={'total_amount': 'Total Refunded (₹)', 'category': 'Category'}
                )
                st.plotly_chart(fig, width='stretch')
        
        with col2:
            if not refund_stats['refund_reasons'].empty:
                fig = px.pie(
                    refund_stats['refund_reasons'],
                    values='count',
                    names='reason',
                    title='Refund Reasons'
                )
                st.plotly_chart(fig, width='stretch')
    
    # ==================== TAB 4: CONVERSATIONS ====================
    with tab4:
        st.header("💬 Recent Conversations")
        
        # Filters
        col1, col2 = st.columns([2, 1])
        with col1:
            search_user = st.text_input("🔍 Search by User ID", placeholder="Enter user ID...")
        with col2:
            limit = st.number_input("Show conversations", min_value=5, max_value=100, value=20, step=5)
        
        # Get conversations
        conversations = get_recent_conversations(limit=limit, user_id=search_user if search_user else None)
        
        if conversations.empty:
            st.info("No conversations found")
        else:
            # Display conversations
            for user_id in conversations['user_id'].unique():
                user_convs = conversations[conversations['user_id'] == user_id]
                
                with st.expander(f"👤 User: {user_id} ({len(user_convs)} messages)"):
                    for idx, msg in user_convs.iterrows():
                        if msg['from'] == 'user':
                            st.markdown(f"**👤 User** ({msg['timestamp'].strftime('%H:%M:%S')}): {msg['text']}")
                        else:
                            st.markdown(f"**🤖 Bot** ({msg['timestamp'].strftime('%H:%M:%S')}): {msg['text']}")
                        st.markdown("---")
    
    # Auto-refresh logic
    if auto_refresh:
        import time
        time.sleep(30)
        st.rerun()


if __name__ == "__main__":
    main()
