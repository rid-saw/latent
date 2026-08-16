"""Block agent: the supervisor routes, the connector fetches.

  START -> supervisor -> fetch -> END

There was a second agent here — a critic that read the fetched items, dropped
the ones it judged off topic, and could rewrite the search terms for one more
round. It was removed after being measured: across four blocks it changed
nothing the user could see, while costing an LLM call every time.

That was not bad luck. It could only delete, never reorder, so it could only
change a block by killing something inside the first max_items — and anything
below that was going to be trimmed away regardless. To have any effect at all
it needed the fetch to pull three times what the block showed, and two guards
existed solely to undo its mistakes: one put items back when it pruned a block
below the requested count, another threw away a second round that returned
less than the first. Deleting it took all of that with it.
"""

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agents.nodes.supervisor import supervisor_node
from app.agents.state import BlockAgentState
from app.services.fetch import fetch_for


async def fetch_node(state: BlockAgentState) -> dict:
    """Hand the supervisor's answers to the one dispatcher and keep the items.

    Deliberately thin. Refresh runs the same function off the plan stored on
    the block, and the two paths drifting apart is what let a refresh quietly
    return something plainer than what was created.
    """
    return {"items": await fetch_for(dict(state))}


@lru_cache
def get_graph():
    g = StateGraph(BlockAgentState)
    g.add_node("supervisor", supervisor_node)
    g.add_node("fetch", fetch_node)
    g.add_edge(START, "supervisor")
    g.add_edge("supervisor", "fetch")
    g.add_edge("fetch", END)
    return g.compile()


async def run_block_agent(query: str) -> BlockAgentState:
    return await get_graph().ainvoke({"query": query})
