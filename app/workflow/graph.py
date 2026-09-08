from langgraph.graph import END, START, StateGraph

from app.agents.association_analysis import association_analysis_node
from app.agents.coordinator import coordinator_node
from app.agents.decision import decision_node
from app.agents.dynamic_prediction import dynamic_prediction_node
from app.agents.evidence import evidence_node, route_after_evidence
from app.agents.human_review import human_review_node
from app.agents.policy_retrieval import policy_retrieval_node
from app.agents.risk_identification import risk_identification_node
from app.workflow.state import WorkflowState


def build_workflow():
    graph = StateGraph(WorkflowState)
    graph.add_node("coordinator", coordinator_node)
    graph.add_node("risk_identification", risk_identification_node)
    graph.add_node("association_analysis", association_analysis_node)
    graph.add_node("dynamic_prediction", dynamic_prediction_node)
    graph.add_node("evidence", evidence_node)
    graph.add_node("policy_retrieval", policy_retrieval_node)
    graph.add_node("decision", decision_node)
    graph.add_node("human_review", human_review_node)

    graph.add_edge(START, "coordinator")
    graph.add_edge("coordinator", "risk_identification")
    graph.add_edge("risk_identification", "association_analysis")
    graph.add_edge("association_analysis", "dynamic_prediction")
    graph.add_edge("dynamic_prediction", "evidence")
    graph.add_conditional_edges(
        "evidence",
        route_after_evidence,
        {"decision": "policy_retrieval", "human_review": "human_review"},
    )
    graph.add_edge("policy_retrieval", "decision")
    graph.add_edge("decision", "human_review")
    graph.add_edge("human_review", END)
    return graph.compile()
