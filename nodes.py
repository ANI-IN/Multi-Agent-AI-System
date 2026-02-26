"""
Nodes module containing all node functions for the multi-agent graph.
"""

import ast
import logging
from typing import Optional

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore
from langgraph.types import interrupt

from state import State
from models import UserInput, UserProfile
from prompts import (
    generate_music_assistant_prompt,
    STRUCTURED_EXTRACTION_PROMPT,
    VERIFICATION_PROMPT,
    CREATE_MEMORY_PROMPT,
)
from database import get_db

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────

def get_customer_id_from_identifier(identifier: str) -> Optional[int]:
    """
    Retrieve Customer ID using an identifier (customer ID, email, or phone).
    Returns the CustomerId if found, otherwise None.
    """
    if not identifier or not identifier.strip():
        return None

    db = get_db()
    identifier = identifier.strip()

    try:
        # Direct numeric customer ID
        if identifier.isdigit():
            result = db.run(f"SELECT CustomerId FROM Customer WHERE CustomerId = {identifier};")
            if result and result.strip() != "[]":
                return int(identifier)
            return None

        # Phone number (starts with + or contains digits with formatting)
        elif identifier.startswith("+") or (
            len(identifier) > 5
            and identifier.replace("-", "").replace(" ", "").replace("(", "").replace(")", "").replace("+", "").isdigit()
        ):
            query = f"SELECT CustomerId FROM Customer WHERE Phone = '{identifier}';"
            result = db.run(query)
            if result and result.strip() != "[]":
                formatted = ast.literal_eval(result)
                if formatted:
                    return formatted[0][0]

        # Email address
        elif "@" in identifier:
            query = f"SELECT CustomerId FROM Customer WHERE Email = '{identifier}';"
            result = db.run(query)
            if result and result.strip() != "[]":
                formatted = ast.literal_eval(result)
                if formatted:
                    return formatted[0][0]
    except Exception as e:
        logger.error(f"Error looking up customer by identifier '{identifier}': {e}")

    return None


def format_user_memory(user_data: dict) -> str:
    """Formats music preferences from stored user data."""
    try:
        profile = user_data.get("memory")
        if profile and hasattr(profile, "music_preferences") and profile.music_preferences:
            return f"Music Preferences: {', '.join(profile.music_preferences)}"
    except Exception as e:
        logger.error(f"Error formatting user memory: {e}")
    return ""


# ─────────────────────────────────────────────
# Music Assistant Node
# ─────────────────────────────────────────────

def create_music_assistant_node(llm, music_tools):
    """Factory function to create the music assistant node with bound tools."""
    llm_with_tools = llm.bind_tools(music_tools)

    def music_assistant(state: State, config: RunnableConfig):
        memory = state.get("loaded_memory", "None") or "None"
        prompt = generate_music_assistant_prompt(memory)

        messages = [SystemMessage(content=prompt)]
        if state.get("customer_id"):
            messages.append(
                SystemMessage(content=f"The current verified customer ID is: {state['customer_id']}")
            )
        messages.extend(state["messages"])

        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    return music_assistant


# ─────────────────────────────────────────────
# Conditional Edge Functions
# ─────────────────────────────────────────────

def should_continue(state: State, config: RunnableConfig) -> str:
    """Determine if the music sub-agent should continue calling tools or end."""
    messages = state["messages"]
    last_message = messages[-1]
    if not last_message.tool_calls:
        return "end"
    return "continue"


def should_interrupt(state: State, config: RunnableConfig) -> str:
    """Determine if customer verification is complete or needs input."""
    if state.get("customer_id") is not None:
        return "continue"
    return "interrupt"


# ─────────────────────────────────────────────
# Verification Nodes
# ─────────────────────────────────────────────

def create_verify_info_node(llm):
    """Factory function to create the verify_info node."""
    structured_llm = llm.with_structured_output(schema=UserInput)

    def verify_info(state: State, config: RunnableConfig):
        """Verify customer account by parsing input and matching with database."""
        if state.get("customer_id") is not None:
            return None  # Already verified, pass through

        user_input = state["messages"][-1]

        try:
            parsed_info = structured_llm.invoke(
                [SystemMessage(content=STRUCTURED_EXTRACTION_PROMPT)] + [user_input]
            )
            identifier = parsed_info.identifier
        except Exception as e:
            logger.error(f"Error parsing user input for verification: {e}")
            identifier = ""

        customer_id = None
        if identifier:
            customer_id = get_customer_id_from_identifier(identifier)

        if customer_id is not None:
            # Inject a system message that clearly states the customer_id
            # so downstream agents (invoice, music) can see it in context
            intent_message = SystemMessage(
                content=(
                    f"Customer verified successfully. "
                    f"The verified customer_id is {customer_id}. "
                    f"Use this customer_id for all invoice and purchase lookups."
                )
            )
            return {
                "customer_id": str(customer_id),
                "messages": [intent_message],
            }
        else:
            response = llm.invoke(
                [SystemMessage(content=VERIFICATION_PROMPT)] + state["messages"]
            )
            return {"messages": [response]}

    return verify_info


def human_input(state: State, config: RunnableConfig):
    """Node that triggers an interrupt to request human input."""
    user_input = interrupt("Please provide input.")
    return {"messages": [HumanMessage(content=user_input)]}


# ─────────────────────────────────────────────
# Memory Nodes
# ─────────────────────────────────────────────

def load_memory(state: State, config: RunnableConfig, store: BaseStore):
    """Load user's long-term memory (music preferences) into graph state."""
    user_id = str(state.get("customer_id", ""))
    if not user_id:
        return {"loaded_memory": ""}

    namespace = ("memory_profile", user_id)
    try:
        existing_memory = store.get(namespace, "user_memory")
        if existing_memory and existing_memory.value:
            formatted = format_user_memory(existing_memory.value)
            return {"loaded_memory": formatted}
    except Exception as e:
        logger.error(f"Error loading memory for user {user_id}: {e}")

    return {"loaded_memory": ""}


def create_memory_node(llm):
    """Factory function to create the create_memory node."""

    def create_memory(state: State, config: RunnableConfig, store: BaseStore):
        """Analyze conversation and save/update user music preferences."""
        user_id = str(state.get("customer_id", ""))
        if not user_id:
            return None

        namespace = ("memory_profile", user_id)

        try:
            existing_memory = store.get(namespace, "user_memory")
            formatted_memory = ""
            if existing_memory and existing_memory.value:
                mem_dict = existing_memory.value
                profile = mem_dict.get("memory")
                if profile and hasattr(profile, "music_preferences"):
                    formatted_memory = (
                        f"Music Preferences: {', '.join(profile.music_preferences or [])}"
                    )

            # Summarize conversation for the memory prompt
            recent_messages = state["messages"][-10:]
            conversation_summary = "\n".join(
                f"{getattr(msg, 'type', 'unknown')}: {getattr(msg, 'content', '')}"
                for msg in recent_messages
                if getattr(msg, "content", "")
            )

            formatted_prompt = CREATE_MEMORY_PROMPT.format(
                conversation=conversation_summary,
                memory_profile=formatted_memory or "Empty, no existing profile",
            )

            updated_memory = llm.with_structured_output(UserProfile).invoke(
                [SystemMessage(content=formatted_prompt)]
            )

            store.put(namespace, "user_memory", {"memory": updated_memory})
            logger.info(f"Memory updated for customer {user_id}: {updated_memory.music_preferences}")
        except Exception as e:
            logger.error(f"Error creating/updating memory for user {user_id}: {e}")

    return create_memory
