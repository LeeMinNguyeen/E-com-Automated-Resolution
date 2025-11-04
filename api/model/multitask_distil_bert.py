from transformers import AutoTokenizer, DistilBertPreTrainedModel, DistilBertModel
import torch.nn as nn


class MultiTaskDistilBert(DistilBertPreTrainedModel):
    def __init__(self, config, num_intent_labels, num_sentiment_labels):
        super().__init__(config)
        self.distilbert = DistilBertModel(config)
        
        # Classifier head for Intent
        self.intent_classifier = nn.Linear(config.dim, num_intent_labels)
        # Classifier head for Sentiment
        self.sentiment_classifier = nn.Linear(config.dim, num_sentiment_labels)
        
        # Initialize weights
        self.init_weights()

    def forward(
        self,
        input_ids=None,
        attention_mask=None,
        head_mask=None,
        inputs_embeds=None,
        labels=None,  # Not used directly here, handled in training loop
        output_attentions=None,
        output_hidden_states=None,
        return_dict=None,
    ):
        return_dict = return_dict if return_dict is not None else self.config.use_return_dict

        # Get the last hidden state from the base DistilBERT model
        distilbert_output = self.distilbert(
            input_ids=input_ids,
            attention_mask=attention_mask,
            head_mask=head_mask,
            inputs_embeds=inputs_embeds,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
            return_dict=return_dict,
        )

        # Get the [CLS] token representation (for classification)
        pooled_output = distilbert_output[0][:, 0]  # [batch_size, hidden_dim]

        # Pass the output through each specific classifier head
        intent_logits = self.intent_classifier(pooled_output)
        sentiment_logits = self.sentiment_classifier(pooled_output)

        # Return the logits for both tasks
        return (intent_logits, sentiment_logits)