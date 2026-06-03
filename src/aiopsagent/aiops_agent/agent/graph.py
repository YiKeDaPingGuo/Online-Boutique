from __future__ import annotations

from langgraph.graph import END, StateGraph

from aiops_agent.datasource.factory import make_datasource
from aiops_agent.detectors import PaperAlgorithmAdapter, RuleBasedDetector
from aiops_agent.diagnosis import RootCauseAnalyzer
from aiops_agent.remediation import ActionExecutor, RemediationPlanner
from aiops_agent.reports import ReportGenerator
from aiops_agent.types import AgentState


def collect_metrics(state: AgentState) -> AgentState:
    try:
        datasource = make_datasource(state["config"])
        state["metrics"] = datasource.collect()
    except Exception as exc:
        state["errors"].append(f"collect_metrics failed: {exc}")
        state["metrics"] = []
    return state


def detect_anomalies(state: AgentState) -> AgentState:
    detector = RuleBasedDetector(state["config"].detector)
    if state["config"].detector.type == "paper":
        active_detector = PaperAlgorithmAdapter(detector)
    else:
        active_detector = detector
    state["anomalies"] = active_detector.detect(state["metrics"])
    return state


def analyze_root_cause(state: AgentState) -> AgentState:
    analyzer = RootCauseAnalyzer(top_k=state["config"].top_k)
    state["root_causes"] = analyzer.rank(state["anomalies"])
    return state


def plan_remediation(state: AgentState) -> AgentState:
    planner = RemediationPlanner(state["config"])
    state["actions"] = planner.suggest(state["root_causes"], state["anomalies"])
    return state


def execute_actions(state: AgentState) -> AgentState:
    executor = ActionExecutor(state["config"])
    state["executed_actions"] = executor.execute(state["actions"])
    return state


def generate_report(state: AgentState) -> AgentState:
    generator = ReportGenerator(state["config"])
    state["report"] = generator.generate(
        metrics=state["metrics"],
        anomalies=state["anomalies"],
        root_causes=state["root_causes"],
        actions=state["actions"],
        executed_actions=state["executed_actions"],
        errors=state["errors"],
    )
    return state


def has_anomaly(state: AgentState) -> str:
    return "yes" if state["anomalies"] else "no"


def build_graph(config):
    graph = StateGraph(AgentState)
    graph.add_node("collect_metrics", collect_metrics)
    graph.add_node("detect_anomalies", detect_anomalies)
    graph.add_node("analyze_root_cause", analyze_root_cause)
    graph.add_node("plan_remediation", plan_remediation)
    graph.add_node("execute_actions", execute_actions)
    graph.add_node("generate_report", generate_report)

    graph.set_entry_point("collect_metrics")
    graph.add_edge("collect_metrics", "detect_anomalies")
    graph.add_conditional_edges(
        "detect_anomalies",
        has_anomaly,
        {
            "yes": "analyze_root_cause",
            "no": "generate_report",
        },
    )
    graph.add_edge("analyze_root_cause", "plan_remediation")
    graph.add_edge("plan_remediation", "execute_actions")
    graph.add_edge("execute_actions", "generate_report")
    graph.add_edge("generate_report", END)
    return graph.compile()
