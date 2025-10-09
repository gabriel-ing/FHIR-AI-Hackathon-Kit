import iris
from langchain_ollama import OllamaLLM 
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from sentence_transformers import SentenceTransformer
from Utils.get_iris_connection import get_cursor
import logging
import warnings

warnings.filterwarnings("ignore")
logging.disable(logging.CRITICAL)


class RAGChatbot:
    def __init__(self):
        self.message_count = 0
        self.cursor = get_cursor()
        self.conversation = self.create_conversation()
        self.embedding_model = self.get_embedding_model()
        

    def get_embedding_model(self):
        return  SentenceTransformer('all-MiniLM-L6-v2') 
        
    def create_conversation(self):
        system_prompt = "You are a helpful and knowledgeable assistant designed to help a doctor interpret a patient's medical history using retrieved information from a database.\
        Please provide a detailed and medically relevant explanation, \
        include the dates of the information you are given."
        ## instanciate the conversation: 
        llm=OllamaLLM(model="gemma3:1b", system=system_prompt) 
        memory = ConversationBufferMemory()
        conversation = ConversationChain(llm=llm, memory=memory)
        return conversation
        
    def vector_search(self, user_prompt,patient):
        search_vector =  self.embedding_model.encode(user_prompt, normalize_embeddings=True, show_progress_bar=False).tolist() 
        
        search_sql = f"""
            SELECT TOP 3 ClinicalNotes 
            FROM VectorSearch.DocRefVectors
            WHERE PatientID = {patient}
            ORDER BY VECTOR_COSINE(NotesVector, TO_VECTOR(?,double)) DESC
        """
        self.cursor.execute(search_sql,[str(search_vector)])
        
        results = self.cursor.fetchall()
        return results

    def run(self):
        if self.message_count==0:
            query = input("\n\nHi, I'm a chatbot used for searching a patient's medical history. How can I help you today? \n\n - User: ")
        else:
            query = input("\n - User:")
        search = True
        if self.message_count != 0:
            search_ans = input("- Search the database? [Y/N - default N]")
            if search_ans.lower() != "y":
                search = False

        if search:
            try:
                patient_id = int(input("- What is the patient ID? "))
            except:
                print("ERROR: The patient ID should be an integer")
                print("Exiting. Please send another prompt.")
                return

            results = self.vector_search(query, patient_id)
            if results == []:
                print("No results found, check patient ID")
                return

            prompt = f"CONTEXT:\n{results}\n\nUSER QUESTION:\n{query}"
        else:
            prompt = f"USER QUESTION:\n{query}"

        ##print(prompt)
        response = self.conversation.predict(input=prompt)
        
        print("- Chatbot: "+ response)
        self.message_count += 1


if __name__=="__main__":
    bot = RAGChatbot()
    while True:
        bot.run()