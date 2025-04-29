from typing import Literal
import uuid
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from tools import search_course_documents_tool
from dl_agents import teacher_agent, quiz_agent, student_input_node
from state import State
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage
from langchain_core.messages.tool import ToolMessage
from langgraph.types import interrupt, Command

tools = [search_course_documents_tool]
tool_node = ToolNode(tools)

def should_continue(state: State) -> Literal["teacher_agent","call_tool", "quiz_agent", "student_input_node",  "__end__"]:
    messages = state["messages"]
    is_asking_for_quiz = state.get("is_asking_for_quiz", False)
    last_message = messages[-1]
    
    if last_message.content == '' and last_message.tool_calls:
        return "call_tool"
    
    if is_asking_for_quiz:
        return "quiz_agent"
    
    return "__end__"

def worker_should_continue(state: State) -> Literal["teacher_agent","call_tool","student_input_node"]:
    messages = state["messages"]
    last_message = messages[-1]
    
    if last_message.content == '' and last_message.tool_calls:
        return "call_tool"
    else:
        return "student_input_node"
    
workflow = StateGraph(State)

# Define the two nodes we will cycle between
workflow.add_node("teacher_agent", teacher_agent)
workflow.add_node("quiz_agent", quiz_agent)
workflow.add_node("tool_node", tool_node)
workflow.add_node("student_input_node", student_input_node)
# edges between the nodes
workflow.add_edge(START, "teacher_agent")

workflow.add_conditional_edges(
        "teacher_agent",
        should_continue,
        {
            "quiz_agent": "quiz_agent", 
            "call_tool": "tool_node",
            "__end__": END
        },
)
workflow.add_conditional_edges(
    "quiz_agent", 
    worker_should_continue, 
    {
        "call_tool": "tool_node",
        "teacher_agent": "teacher_agent",
        "student_input_node": "student_input_node",
    }
)

workflow.add_edge("student_input_node", "quiz_agent")

workflow.add_conditional_edges(
    "tool_node",
    lambda x: x["sender"],
    {
        "quiz_agent": "quiz_agent",
        "teacher_agent": "teacher_agent",
    }
)

#quiz on traffic signs, choose topics
def main():
    # A checkpointer is required for `interrupt` to work.
    checkpointer = MemorySaver()
    graph = workflow.compile(checkpointer=checkpointer)
    # Pass a thread ID to the graph to run it.
    thread_config = {"configurable": {"thread_id": uuid.uuid4()}}

    while True:
        user_init = input("user answer : ")

        if "user_gave_answer" in graph.get_state(thread_config).values:
                if graph.get_state(thread_config).values["user_gave_answer"] == True:
                    # Resume using Command
                    for chunk in graph.stream(Command(resume=user_init), config=thread_config, stream_mode='values'):
                        chunk["messages"][-1].pretty_print()
                        print("\n")


        for chunk in graph.stream({"messages": HumanMessage(content=user_init)}, config=thread_config, stream_mode='values'):
            chunk["messages"][-1].pretty_print()
            print("\n")

        if user_init.lower() == "quit":
            print("Exiting the program.")
            break
if __name__ == "__main__":
    main()

# from typing import Literal, TypedDict
# import uuid
# from langgraph.checkpoint.memory import MemorySaver
# from langgraph.constants import START
# from langgraph.graph import StateGraph
# from langgraph.types import interrupt, Command

# class State(TypedDict):
#    """The graph state."""
#    human_node_answer: str
#    quiz_agent_question: str

# def quiz_agent(state: State) -> Command[Literal["human_node"]]:
#     print("i am quiz_agent and i am running.. running running ..")
#     quiz_agent_question = "What is the capital of France?"
#     return Command(
#         # state update
#         update={"quiz_agent_question": quiz_agent_question},
#         # control flow
#         goto="human_node"
#     )

# def teacher_agent(state: State):
#     print("i am teacher_agent and i am running.. running running ..")
#     human_node_answer = state["human_node_answer"]
#     print(f"Received answer from human node: {human_node_answer}")

# def human_node(state: State):
#     print("i am human_node and i am running.. running running ..")
#     value = interrupt(
#         {
#             "quiz_agent_question": state["quiz_agent_question"]
#         }
#     )
#     return {
#         "human_node_answer": value
#     }

# # Build the graph
# graph_builder = StateGraph(State)
# graph_builder.add_node("human_node", human_node)
# graph_builder.add_node("quiz_agent", quiz_agent)
# graph_builder.add_node("teacher_agent", teacher_agent)

# graph_builder.add_edge(START, "quiz_agent")
# graph_builder.add_edge("quiz_agent", "human_node")
# graph_builder.add_edge("human_node", "teacher_agent")

# def main():
#     # A checkpointer is required for `interrupt` to work.
#     checkpointer = MemorySaver()
#     graph = graph_builder.compile(checkpointer=checkpointer)

#     # Pass a thread ID to the graph to run it.
#     thread_config = {"configurable": {"thread_id": uuid.uuid4()}}

#     user_init = input("Enter something (type 'quit' to exit): ")
#     # Using stream() to directly surface the `__interrupt__` information.
#     for chunk in graph.stream({"human_node_answer": user_init}, config=thread_config):
#         print(chunk)
#         print("\n")

#     user_answer = input("Enter something (type 'quit' to exit): ")
#     # Resume using Command
#     for chunk in graph.stream(Command(resume=user_answer), config=thread_config):
#         print(chunk)
#         print("\n")


# if __name__ == "__main__":
#     main()