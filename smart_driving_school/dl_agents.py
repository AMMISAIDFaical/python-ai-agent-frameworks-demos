from typing import Literal
from state import Quiz, State, QuizList
from prompts import teacher_prompt, quiz_prompt
from model import load_model
from tools import quiz_preparation_tool, search_course_documents_tool, teacher_understanding_tool
from langgraph.types import interrupt, Command
from langchain_core.messages import AIMessage

def teacher_agent(state: State):
    messages = state.get("messages", [])
    is_asking_for_quiz = state.get("is_asking_for_quiz", False)
    last_message = messages[-1]
    quiz_topics = state.get("quiz_topics", [])
    model = load_model()
    model = model.bind_tools([quiz_preparation_tool, teacher_understanding_tool,search_course_documents_tool])
    chain = teacher_prompt | model
    response =chain.invoke({"messages": messages})
    
    # Check if the response contains tool calls
    #case the teacher agent called the quiz preparation tool to extract quiz topics
    for calls in response.tool_calls:
        if calls['name'] == "teacher_understanding_tool":
            return {
                "messages": calls['args']['clarifying_question'], 
                "sender": "teacher_agent"
            }
        if calls['name'] == "quiz_preparation_tool":
            return {
                "quiz_topics": calls['args']['quiz_covered_topics'], 
                "quiz_study_material": calls['args']['theory_study_material'],
                "sender": "teacher_agent",
                "is_asking_for_quiz": True
            }
        # other tools and not the quiz topic extractor tool was called
        else:
            return {
                "messages": response,
                "sender": "teacher_agent"
            }
    response.name = "teacher_agent"
    # If no tool calls were made, return the response as is
    return {
                "messages": response
            }

def quiz_agent(state: State):
    messages = state.get("messages", [])
    last_message = messages[-1]
    quiz_history = state.get("quiz_history", [])
    if last_message.name == "student":
        for quiz in quiz_history:
            return Command(
                update={
                    "messages": AIMessage(
                        content =quiz.question + '\n' +
                        'Hint : ' + '\n' + 
                        quiz.hint + '\n' + 
                        'Here are the choices : ' + '\n' +
                        str(quiz.mutliple_choices),
                        name="quiz_agent" 
                    ),
                    "sender": "quiz_agent",
                    "is_asking_for_quiz": False,
                    "user_gave_answer": True,
                },
                goto="student_input_node"
            )

    quiz_history = state.get("quiz_history", [])
    quiz_topics = state.get("quiz_topics", [])
    quiz_study_material = state.get("quiz_study_material", "")
    model = load_model()
    model = model.with_structured_output(QuizList)
    chain = quiz_prompt | model

    response = chain.invoke(
        {
            "messages": messages,
            "quiz_topics": quiz_topics,
            "quiz_study_material": quiz_study_material
        }
)
def student_input_node(state: State) -> Command[Literal["teacher_agent", "quiz_agent"]]:
    # def human_node(state: State):
    print("i am human_node and i am running.. running running ..")
    value = interrupt(
        {
            "messages": state["messages"][-1].content,
        }
    )
    return Command(
        # state update
        update={
            "messages":value,
            "user_answer": value,
            "user_gave_answer": True
        },
        # control flow
        goto="quiz_agent"
    )
