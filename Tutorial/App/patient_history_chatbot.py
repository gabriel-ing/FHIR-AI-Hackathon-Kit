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
        self.patient_id = 0

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

    def set_patient_id(self, patient_id):
        self.patient_id=patient_id

    def run(self, user_prompt: str, do_search: bool = True) -> str:
        """
        Execute one turn of the chat. Returns the assistant's reply as a string.
        Requires self.patient_id to be set before calling if do_search is True.
        """
        if do_search:
            if not self.patient_id:
                raise ValueError("Patient ID is not set. Call set_patient_id(...) first.")
            results = self.vector_search(user_prompt, self.patient_id)
            if results == []:
                # Optional: keep going but with an explicit note
                context = "No results found for this patient ID."
            else:
                # Assumes rows like [(ClinicalNotes,), ...]
                context_parts = []
                for r in results:
                    text = r[0] if isinstance(r, (list, tuple)) and len(r) == 1 else str(r)
                    context_parts.append(str(text))
                context = "\n---\n".join(context_parts)
            prompt = f"CONTEXT:\n{context}\n\nUSER QUESTION:\n{user_prompt}"
        else:
            prompt = f"USER QUESTION:\n{user_prompt}"

        response = self.conversation.predict(input=prompt)
        self.message_count += 1
        return response

    def reset(self):
        self.message_count = 0
        self.conversation = self.create_conversation()
        # keep the same patient, or also reset it if you prefer:
        # self.patient_id = 0



if __name__=="__main__":
    bot = RAGChatbot()
    while True:
        bot.run()