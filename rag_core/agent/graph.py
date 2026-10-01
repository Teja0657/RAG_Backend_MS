from langgraph.graph import StateGraph, START, END

from rag_core.agent.state import RagState
from rag_core.agent.nodes import retrieve_node, rerank_node, generate_node


def build_graph():
    graph = StateGraph(RagState)

    graph.add_node("retrieve", retrieve_node)
    graph.add_node("rerank", rerank_node)
    graph.add_node("generate", generate_node)

    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "rerank")
    graph.add_edge("rerank", "generate")
    graph.add_edge("generate", END)

    return graph.compile()


rag_graph = build_graph()
