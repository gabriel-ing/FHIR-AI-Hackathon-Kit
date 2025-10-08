### Brief Introduction to Retrieval Augmented Generation

Retrieval Augmented Generation (RAG) is a popular method to turn generalised Large Language Models (like chatGPT) into subject specialists, with up-to-date and verified information.  

The idea is simple, when a user sends a query, this prompt is first used to search a database of relevant information. The results of the database search is combined with the user's query and sent to the LLM. This is combined with a system prompt, instructing the LLM to use only the information provided in the search results. 

![image.png](attachment:bdad4667-cf4a-4ecd-a9ef-6df0e39cf455.png)

This simple architechture can create a chatbot which has all the relevant and up-to-date information without requiring expensive fine-tuning or re-training. This architecture also allows the data in the database to be kept private, i.e. not used to train the model. 

#### Vector Search

The database search is best performed with a Vector search. Plain text information is transformed to Vectors, which places the text at a specific point in multi-dimensional, where each dimension may describe some abstract quality or semantic meaning in text. 

By using vectors rather than raw text, the meaning behind the text is searched, rather than searching for keywords in the text. 

When a user sends a query, this is then also transformed into a vector with the same embedding model. The most similar text in the database is then returned. 

#### Considerations
There are several things that can affect the performance of the vector search and RAG chatbot: 
- The choice of Embedding Model will affect the quality of the vector search. Some embedding models have been created for specific types of text, for example for use with medical or scientific information. This improvement comes at a cost, more specific or larger models tend to be slower to perform the embedding. 
- The Number of Dimensions in our vector will affect both quality and performance. Dimensionality is generally decided by the embedding model. More dimensions will lead to better search results but will slow performance.
- The choice of LLM is vital. In this tutorial I will demonstrate using both a local downloaded model and a only model accessed through an API. Using a local LLM will come with a huge performance cost, as the models need to be downloadable (and therefore small in size) and are slow to return results. However local models may be vital for keeping patient data private and on-site, rather than send it to an external server.

#### More info

This was a very brief introduction, but for more information you can check out some of the following links: 
- What is RAG? https://youtu.be/u47GtXwePms
- Code-to-Care video series https://www.youtube.com/playlist?list=PLG6AFWumOYWhyM8T2Doye4sAA-kOH6-YG