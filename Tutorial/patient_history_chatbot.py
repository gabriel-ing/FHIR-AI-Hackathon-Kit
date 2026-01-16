import iris
from langchain_ollama import OllamaLLM 
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from sentence_transformers import SentenceTransformer
from ..Utils.get_iris_connection import get_cursor
import logging
import warnings

warnings.filterwarnings("ignore")
logging.disable(logging.CRITICAL)

import iris
class RAGChatbot:
    def __init__(self):
        self.message_count = 0
        conn = iris.connect("localhost", 32782, "DEMO", "_SYSTEM", "ISCDEMO") # Server, Port , Namespace, Username, Password
        self.cursor = conn.cursor()
        self.agent = self.create_agent()
        self.embedding_model = self.get_embedding_model()
        

    
    def get_embedding_model(self):
        return  SentenceTransformer('all-MiniLM-L6-v2') 
        
    def create_agent(self):



        # Initialize model
        llm = ChatOllama(model="gemma3:1b") 
        
        # Initialise short-term memory
        checkpointer = InMemorySaver()
        
        # Create model
        agent = create_agent(
            model=llm, # Set model as our LLM 
            middleware=[
                # create summarization proceedure - this creates summaries of our conversation to keep memory brief.
                SummarizationMiddleware(
                    model=llm,
                    max_tokens_before_summary=4000,  # Trigger summarization at 4000 tokens
                    messages_to_keep=20,  # Keep last 20 messages after summary
                )
            ],
            # Creates the agent's memory with pre-initialized model
            checkpointer=checkpointer,
        )
        self.config = {"configurable": {"thread_id": "1"}}
        return agent
        
    def vector_search(self, user_prompt,patient):
        search_vector =  self.embedding_model.encode(user_prompt, normalize_embeddings=True, show_progress_bar=False).tolist() 
        
        search_sql = f"""
            SELECT TOP 3 ClinicalNotes 
            FROM VectorSearch.DocRefVectors
            WHERE PatientID = ?
            ORDER BY VECTOR_COSINE(NotesVector, TO_VECTOR(?,double)) DESC
        """
        self.cursor.execute(search_sql,[patient, str(search_vector)])
        
        results = self.cursor.fetchall()
        return results

    def run(self):
        if self.message_count==0:

            
            query = input("\n\nHi, I'm a chatbot used for searching a patient's medical history. How can I help you today? \n\n - User: ")
        else:
            query = input("\n - User:")
        search = True
        if self.message_count != 0:
            search_ans = input("Search the database? [Y/N - default N]")
            if search_ans.lower() != "y":
                search = False

        if search:
            try:
                patient_id = int(input("What is the patient ID?"))
            except:
                print("The patient ID should be an integer")
                return

            results = self.vector_search(query, patient_id)
            if results == []:
                print("No results found, check patient ID")
                return

            prompt = f"CONTEXT:\n{results}\n\nUSER QUESTION:\n{query}"
        else:
            prompt = f"USER QUESTION:\n{query}"

        ##print(prompt)
        system_prompt = "You are a helpful and knowledgeable assistant designed to help a doctor interpret a patient's medical history using retrieved information from a database.\
        Please provide a detailed and medically relevant explanation, \
        include the dates of the information you are given."
        response = self.agent.invoke({"messages" : [("system", system_prompt), ("user", query), ("system", str(results))]}, self.config)
        response["messages"][-1].pretty_print()
        self.message_count += 1




if __name__=="__main__":
    bot = RAGChatbot()
    while True:
        bot.run()