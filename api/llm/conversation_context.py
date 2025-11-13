"""
Conversation context tracking utilities.
Helps track what information the bot has asked for and what it's waiting for.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ConversationContext:
    """
    Tracks conversation context for a user session.
    Helps determine if we're waiting for specific information.
    """
    
    def __init__(self):
        # Store contexts per user_id
        self._contexts: Dict[str, Dict] = {}
    
    def get_context(self, user_id: str) -> Dict:
        """Get conversation context for a user."""
        if user_id not in self._contexts:
            self._contexts[user_id] = {
                'waiting_for': None,  # What information we're waiting for
                'last_bot_question': None,  # Last question bot asked
                'pending_action': None,  # Action pending info (e.g., 'refund', 'order_lookup')
                'extracted_info': {},  # Info extracted so far
                'last_nlu_result': None,  # Cached NLU result
                'last_nlu_timestamp': None,  # When NLU was last run
                'last_message_timestamp': None  # When last message was received
            }
        return self._contexts[user_id]
    
    def should_run_nlu(self, user_id: str) -> bool:
        """
        Determine if NLU analysis should be run for this message.
        
        Run NLU if:
        1. First message (no previous NLU result)
        2. Message is 24+ hours after last message (new session)
        3. Explicitly requested by LLM (handled separately)
        
        Args:
            user_id: User identifier
            
        Returns:
            True if NLU should be run, False otherwise
        """
        context = self.get_context(user_id)
        
        # First message - always run NLU
        if context['last_nlu_result'] is None:
            return True
        
        # Check if last message was 24+ hours ago
        if context['last_message_timestamp']:
            last_msg_time = context['last_message_timestamp']
            time_diff = datetime.now() - last_msg_time
            
            # If 24 hours passed, treat as new session
            if time_diff >= timedelta(hours=24):
                logger.info(f"User {user_id}: 24+ hours since last message, running NLU")
                return True
        
        # Otherwise, use cached NLU result
        return False
    
    def update_nlu_result(self, user_id: str, nlu_result: Dict):
        """
        Store NLU result and timestamp.
        
        Args:
            user_id: User identifier
            nlu_result: NLU analysis result
        """
        context = self.get_context(user_id)
        context['last_nlu_result'] = nlu_result
        context['last_nlu_timestamp'] = datetime.now()
        logger.info(f"User {user_id}: Cached NLU result - {nlu_result.get('intent')} / {nlu_result.get('sentiment')}")
    
    def get_cached_nlu_result(self, user_id: str) -> Optional[Dict]:
        """
        Get cached NLU result if available.
        
        Args:
            user_id: User identifier
            
        Returns:
            Cached NLU result or None
        """
        context = self.get_context(user_id)
        return context.get('last_nlu_result')
    
    def update_message_timestamp(self, user_id: str):
        """Update the timestamp of the last message received."""
        context = self.get_context(user_id)
        context['last_message_timestamp'] = datetime.now()
    
    def clear_nlu_cache(self, user_id: str):
        """Clear cached NLU result (e.g., when topic changes)."""
        context = self.get_context(user_id)
        context['last_nlu_result'] = None
        context['last_nlu_timestamp'] = None
        logger.info(f"User {user_id}: Cleared NLU cache")
    
    def set_waiting_for(self, user_id: str, waiting_for: str, pending_action: str, bot_question: str):
        """
        Mark that we're waiting for specific information.
        
        Args:
            user_id: User identifier
            waiting_for: What we're waiting for (e.g., 'order_id', 'confirmation')
            pending_action: What action is pending (e.g., 'refund', 'order_lookup')
            bot_question: The question the bot asked
        """
        context = self.get_context(user_id)
        context['waiting_for'] = waiting_for
        context['pending_action'] = pending_action
        context['last_bot_question'] = bot_question
        logger.info(f"User {user_id} context: waiting for {waiting_for} for {pending_action}")
    
    def clear_waiting(self, user_id: str):
        """Clear waiting state for a user."""
        context = self.get_context(user_id)
        context['waiting_for'] = None
        context['pending_action'] = None
        context['last_bot_question'] = None
        logger.info(f"User {user_id} context: cleared waiting state")
    
    def is_waiting_for(self, user_id: str, info_type: str) -> bool:
        """Check if we're waiting for specific information."""
        context = self.get_context(user_id)
        return context.get('waiting_for') == info_type
    
    def add_extracted_info(self, user_id: str, key: str, value: any):
        """Add extracted information to context."""
        context = self.get_context(user_id)
        context['extracted_info'][key] = value
        logger.info(f"User {user_id} context: added {key} = {value}")
    
    def get_extracted_info(self, user_id: str, key: str) -> Optional[any]:
        """Get extracted information from context."""
        context = self.get_context(user_id)
        return context['extracted_info'].get(key)
    
    def clear_context(self, user_id: str):
        """Clear all context for a user."""
        if user_id in self._contexts:
            del self._contexts[user_id]
            logger.info(f"User {user_id} context: cleared all context")
    
    def get_context_summary(self, user_id: str) -> str:
        """
        Get a summary of the current context for the LLM.
        
        Returns:
            A string describing what information we have and what we're waiting for
        """
        context = self.get_context(user_id)
        
        summary_parts = []
        
        # What we're waiting for
        if context['waiting_for']:
            summary_parts.append(f"You previously asked for {context['waiting_for']}.")
            summary_parts.append(f"Last question: '{context['last_bot_question']}'")
            summary_parts.append(f"Pending action: {context['pending_action']}")
        
        # What we've extracted
        if context['extracted_info']:
            info_str = ", ".join([f"{k}={v}" for k, v in context['extracted_info'].items()])
            summary_parts.append(f"Information collected: {info_str}")
        
        if summary_parts:
            return "[CONVERSATION CONTEXT]\n" + "\n".join(summary_parts) + "\n"
        
        return ""


# Global instance
_conversation_context = ConversationContext()


def get_conversation_context() -> ConversationContext:
    """Get the global conversation context instance."""
    return _conversation_context
