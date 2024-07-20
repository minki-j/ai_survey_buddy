from varname import nameof as n
from langgraph.graph import END, StateGraph
from langchain_core.runnables import RunnablePassthrough

from app.langchain.schema import StateType
from app.schemas.schemas import State, User, Review, Report
from app.langchain.utils.converters import to_path_map

from app.langchain.nodes.llm.generate import generate_reply
from app.langchain.subgraphs.middle_of_chat.gather_context.graph import gather_context
from app.langchain.subgraphs.middle_of_chat.extract.graph import extract
from app.langchain.subgraphs.middle_of_chat.graph_agent.graph import graph_agent
from app.langchain.nodes.llm.find import (
    find_missing_detail_story_only,
    find_missing_detail_with_reply,
    find_missing_detail_from_customer_perspective,
)
from app.langchain.conditional_edges.llm.reflect import reflect_picked_missing_detail
from app.langchain.nodes.llm.generate import update_story
from app.langchain.nodes.llm.decide import decide_reply_type
from app.langchain.nodes.llm.pick import pick_best_missing_detail
from app.langchain.nodes.non_llm.predefined_reply import reply_for_incomplete_msg
from app.langchain.conditional_edges.llm.check import is_msg_cut_off

from app.langchain.subgraphs.utils.tournament import tournament
from app.langchain.common import USE_TOURNAMENT, USE_IS_MSG_CUT_OFF

g = StateGraph(StateType)
g.set_entry_point("entry")

g.add_node("entry", RunnablePassthrough())
g.add_conditional_edges(
    "entry",
    is_msg_cut_off if USE_IS_MSG_CUT_OFF else lambda x: n(extract),
    to_path_map(
        [
            n(extract),
            n(reply_for_incomplete_msg),
        ]
    ),
)


g.add_node(n(extract), RunnablePassthrough())  # TODO: implement "extract" subgraph

g.add_edge(n(extract), n(gather_context))
g.add_edge(n(extract), n(graph_agent))

g.add_node(n(graph_agent), graph_agent)

g.add_node(n(gather_context), gather_context)
g.add_edge(n(gather_context), n(update_story))

g.add_node(n(update_story), update_story)
g.add_edge(n(update_story), "find_missing_details")

g.add_node("find_missing_details", RunnablePassthrough())
g.add_edge("find_missing_details", n(find_missing_detail_with_reply))

g.add_node(n(find_missing_detail_with_reply), find_missing_detail_with_reply)

if USE_TOURNAMENT:
    g.add_edge("find_missing_details", n(find_missing_detail_story_only))
    g.add_edge("find_missing_details", n(find_missing_detail_from_customer_perspective))

    g.add_node(n(find_missing_detail_story_only), find_missing_detail_story_only)
    g.add_node(
        n(find_missing_detail_from_customer_perspective),
        find_missing_detail_from_customer_perspective,
    )

    g.add_edge(
        [
            n(find_missing_detail_with_reply),
            n(find_missing_detail_story_only),
            n(find_missing_detail_from_customer_perspective),
        ],
        n(tournament),
    )

    g.add_node(n(tournament), tournament)
    g.add_edge(n(tournament), n(generate_reply))
else:
    g.add_edge(n(find_missing_detail_with_reply), n(pick_best_missing_detail))
    # Possible to add story_only and customer_perspective here
    g.add_node(n(pick_best_missing_detail), pick_best_missing_detail)
    g.add_edge(n(pick_best_missing_detail), n(generate_reply))

g.add_node(n(generate_reply), generate_reply)

g.add_node(
    "rendezvous", RunnablePassthrough()
)  # Must declare the node before the type of edge below
g.add_edge(
    [n(generate_reply), n(graph_agent)], "rendezvous"
)  # Must use this format to wait until both graphs are done

g.add_edge("rendezvous", n(decide_reply_type))

g.add_node(n(decide_reply_type), decide_reply_type)
g.add_edge(n(decide_reply_type), END)

g.add_node(n(reply_for_incomplete_msg), reply_for_incomplete_msg)
g.add_edge(n(reply_for_incomplete_msg), END)

middle_of_chat = g.compile()

# with open("graph_imgs/middle_of_chat.png", "wb") as f:
#     f.write(middle_of_chat.get_graph().draw_mermaid_png())
