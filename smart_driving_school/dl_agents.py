from typing import Literal
from state import QuizList, State
from prompts import teacher_prompt, quiz_prompt
from model import load_model
from tools import quiz_preparation_tool, search_course_documents_tool, teacher_understanding_tool
from langgraph.types import interrupt, Command, Send
from langchain_core.messages import AIMessage, HumanMessage

def teacher_agent(state: State):
    messages = state.get("messages", [])
    model = load_model()
    model = model.bind_tools([quiz_preparation_tool, teacher_understanding_tool, search_course_documents_tool])
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
    last_message = state.get("messages", [])[-1]
    quiz_topics = state.get("quiz_topics", [])
    quiz_study_material = state.get("quiz_study_material", "")
    quiz_history = state.get("quiz_history", [])
    if last_message.name != "student" and quiz_history == []:
        model = load_model()
        model = model.with_structured_output(QuizList)
        chain = quiz_prompt | model
        response = chain.invoke({"messages": messages, 
                                 "quiz_topics": quiz_topics, 
                                 "quiz_study_material": quiz_study_material
        })
        for quiz in response.list_of_quiz:
            return {
                "messages": AIMessage(content=str( quiz.question + '\n' + quiz.hint + '\n' + str(quiz.mutliple_choices) + '\n'), name="quiz_agent"),
            }
                                                                              
def student_input_node(state: State) -> Command[Literal["teacher_agent", "quiz_agent"]]:
    quiz_history = state.get("quiz_history", [])
    last_message = state.get("messages", [])[-1]
   
    value = interrupt(
        {
            "messages": last_message,
        }
    )
    return {
        "messages": HumanMessage(content=value, name="student"),
        "user_gave_answer": True,
    }
