"""Block agent: supervisor -> fetch -> critic, with a bounded reflection loop.

  START -> supervisor -> fetch -> critic -> (approved or 2 rounds) -> END
                           ^________________| (refined search terms)
"""

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agents.nodes.critic import critic_node
from app.agents.nodes.supervisor import supervisor_node
from app.agents.state import BlockAgentState
from app.integrations.espn.client import search_sports
from app.integrations.papers.client import search_papers
from app.integrations.gmail.client import search_messages
from app.integrations.news.client import search_news
from app.integrations.seek.client import search_jobs
from app.integrations.websearch.client import search_web
from app.integrations.youtube.client import search_videos

MAX_ROUNDS = 2

_CONNECTORS = {
    "youtube": search_videos,
    "papers": search_papers,
    "gmail": search_messages,
    "news": search_news,
    "sports": search_sports,
    "web": search_web,
}


# The critic drops off-topic items, so fetching exactly max_items leaves the
# block short whenever it prunes anything. Over-fetch and trim afterwards:
# these connectors are free and keyless, and the critic reads one list either
# way, so a wider net costs no extra requests.
OVERFETCH = 3
MAX_FETCH = 15


async def fetch_node(state: BlockAgentState) -> dict:
    source = state["source"]
    terms = state["search_terms"]
    n = min(state.get("max_items", 3) * OVERFETCH, MAX_FETCH)
    if source == "youtube":
        items = await search_videos(terms, max_results=n, latest=state.get("wants_latest", False))
    elif source == "jobs":
        items = await search_jobs(
            terms,
            max_results=n,
            location=state.get("location", ""),
            latest=state.get("wants_latest", False),
        )
    elif connector := _CONNECTORS.get(source):
        items = await connector(terms, max_results=n)
    else:
        items = []

    round_n = state.get("iterations", 0) + 1
    prev = state.get("items") or []
    # A refinement that returns less than the round before it made things
    # worse. Keep the better set and the terms that found it: those terms are
    # persisted on the block and reused by every later refresh, so accepting a
    # regression here breaks the block permanently, not just once.
    if round_n > 1 and len(items) < len(prev):
        return {
            "items": prev,
            "search_terms": state.get("prev_terms") or terms,
            "iterations": round_n,
            "regressed": True,
        }
    return {"items": items, "prev_terms": terms, "iterations": round_n}


def _after_critic(state: BlockAgentState) -> str:
    if state.get("approved") or state.get("iterations", 0) >= MAX_ROUNDS:
        return "done"
    return "refine"


@lru_cache
def get_graph():
    g = StateGraph(BlockAgentState)
    g.add_node("supervisor", supervisor_node)
    g.add_node("fetch", fetch_node)
    g.add_node("critic", critic_node)
    g.add_edge(START, "supervisor")
    g.add_edge("supervisor", "fetch")
    g.add_edge("fetch", "critic")
    g.add_conditional_edges("critic", _after_critic, {"refine": "fetch", "done": END})
    return g.compile()


async def run_block_agent(query: str) -> BlockAgentState:
    return await get_graph().ainvoke({"query": query, "iterations": 0})
