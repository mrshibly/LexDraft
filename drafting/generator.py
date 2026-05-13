"""
Calls LLM API (via OpenRouter) with the assembled prompt.
Post-processes citations in the response to link to source chunks.
"""
from __future__ import annotations

import logging
import re
import time
import uuid

from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, LLM_MODEL, LLM_MAX_TOKENS, LLM_TEMPERATURE
from retrieval.models import RetrievalResult, RetrievedChunk
from ingestion.models import StructuredDocumentRecord
from drafting.models import DraftResult
from drafting.prompt_builder import build_prompt

logger = logging.getLogger(__name__)


def generate_draft(
    retrieval_result: RetrievalResult,
    structured_record: StructuredDocumentRecord,
    preference_rules: list[str],
    draft_type_module
) -> DraftResult:
    """Generate a grounded legal draft using LLM via OpenRouter.
    
    Steps:
    1. Build prompt from evidence + fields + preferences + task
    2. Call LLM API
    3. Extract citation labels from response
    4. Build citations_used list from cited chunks
    5. Return DraftResult
    """
    from openai import OpenAI

    # 1. Build prompt
    system_prompt, user_message = build_prompt(
        retrieval_result, structured_record, draft_type_module, preference_rules
    )

    # 2. Call LLM via OpenRouter
    client = OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
    )

    logger.info(f"Generating draft with model {LLM_MODEL}...")
    start_time = time.time()

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            max_tokens=LLM_MAX_TOKENS,
            temperature=LLM_TEMPERATURE,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            extra_headers={
                "HTTP-Referer": "https://lexdraft.local",
                "X-Title": "LexDraft"
            }
        )
    except Exception as e:
        if "rate" in str(e).lower():
            logger.warning("Rate limited — waiting 60s and retrying...")
            time.sleep(60)
            response = client.chat.completions.create(
                model=LLM_MODEL,
                max_tokens=LLM_MAX_TOKENS,
                temperature=LLM_TEMPERATURE,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                extra_headers={
                    "HTTP-Referer": "https://lexdraft.local",
                    "X-Title": "LexDraft"
                }
            )
        else:
            logger.error(f"Draft generation failed: {e}")
            raise RuntimeError(f"Draft generation failed: {e}")

    generation_time_ms = int((time.time() - start_time) * 1000)

    # 3. Extract draft text
    draft_text = response.choices[0].message.content
    if not draft_text:
        raise RuntimeError("LLM returned empty response")

    # 4. Extract citation labels used in the draft
    cited_labels = set(f"[{n}]" for n in re.findall(r'\[(\d+)\]', draft_text))

    # 5. Filter coverage map to only chunks that were actually cited
    citations_used = []
    for label in sorted(cited_labels):
        if label in retrieval_result.coverage_map:
            citations_used.append(retrieval_result.coverage_map[label])

    # 6. Token usage
    tokens_used = 0
    if response.usage:
        tokens_used = response.usage.total_tokens

    # 7. Build result
    draft_id = f"dr_{uuid.uuid4().hex[:8]}"

    result = DraftResult(
        draft_id=draft_id,
        doc_id=retrieval_result.doc_id,
        draft_type=draft_type_module.DRAFT_TYPE_ID,
        draft_text=draft_text,
        citations_used=citations_used,
        preferences_applied=preference_rules,
        model_used=LLM_MODEL,
        tokens_used=tokens_used,
        generation_time_ms=generation_time_ms
    )

    logger.info(
        f"Draft generated: {draft_id}, {len(citations_used)} citations used, "
        f"{tokens_used} tokens, {generation_time_ms}ms"
    )

    return result
