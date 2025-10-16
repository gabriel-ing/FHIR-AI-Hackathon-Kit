# Vibe coding demos 

For people not familiar with the term vibe-coding - this is a term coined by Andrej Karpathy, the OpenAI cofounder. It basically means using a Large Language model (e.g. ChatGPT, Gemini, Claude etc...) to write all the code for the project, meaning a user can create things with code, without having any practical knowledge of what the code is doing. While I can't recommend this approach for final production, it is fantastic as a rapid start, prototyping tool to get you to a minimum viable product (MVP).

## Vibe Coding a FHIR UI with React

There is a great example of how generative AI tools can be used with a FHIR server available on [InterSystems Developer Community](https://community.intersystems.com/post/building-strikeout-prompting-ui-intersystems-fhir-lovable). In particular, [Lovable.dev](https://lovable.dev/) can create effective web applications that link to a FHIR server, just with a prompt and the specification of the FHIR endpoints. 

This was used to create a React.JS front end user interface for the FHIR server with **No Front-end coding knowledge**.

[Read the Article](https://community.intersystems.com/post/building-strikeout-prompting-ui-intersystems-fhir-lovable)
[Watch the walkthrough](https://www.youtube.com/watch?v=NmQipSlYaeg&embeds_referring_euri=https%3A%2F%2Fcommunity.intersystems.com%2F&source_ve_path=MjM4NTE)
[View the App](https://openexchange.intersystems.com/package/React-Native-Frontend-for-FHIR-by-Lovable)


## Vibe Coding a FHIR AI Chatbot with pure Python

With the main tutorial being Python based, I wanted to create a chatbot front-end that could incorporate the Python code from the tutorial, using only 'vibe-coding'. I tried to do this in a couple of ways, in general I didn't find the experience _super_ friendly, but its definitely possible to create a working front-end through vibe-coding. 

### Attempt 1: Using chatGPT to create a Flask application

`flask` is a python package used for creating web applications. It will render an HTML template, and runs python code on the back end. The python functions being used are hosted at REST end-points, meaning you can use the JavaScript in the front end to pass data to the Python back-end. As such, this means you need to create files with Python, HTML, JavaScript and CSS (which formats the HTML). The JavaScript and CSS can be held within the HTML file. I tried to vibe-code a web-app with the following prompt: 

    
    I want to create a flask web application for a chatbot. Work this through step by step and create the requested application.* 

    The chatbot is created by importing the class RAGChatbot from the Patient_history_chatbot.py file and is run by calling bot.run(user_prompt). The relevant patient ID also needs to be provided first. 

    I am providing the relevant file for reference, please comment on any code that needs to be changed. 

    This is a demo product, so does not need any security or measures that you would normally take of production code, just a minimum viable product. It also does not need to save previous chats, but it doesnt need a button to reset the chat. 

    Start by providing the app.py file and then in follow ups I will request the html and css files.

I also included the *patient_history_chatbot.py* file in the prompt. With this initial prompt and two follow up prompts (*Now give me the html/css file*), I built something that worked. The files had to be saved in the following structure: 

    /AppDirectory:
    L app.py
    L templates/
    |   L index.html
    L static/
       L css/
           chat.css

You may wish to input this structure to ensure the links are correct on the output, or alternatively, you can let the model decide how to structure it, just make sure to use the filenames it gives. 

To run the application, you will need to install Flask (`pip install flask`), then simply run the python file: `python app.py`. You should then be able to find the web application at http://localhost:5000, although the port number may be different (It can be specified in the app.py file: `app.run(host="0.0.0.0", port=5000, debug=True)`)


#### Method evaluation

I chose to use this vibe-coding method because I have used flask before, meaning I am quite familiar with it. Even so, it took me three separate attempts to make GPT-5 (run on Copilot) give me successful code. I found that sometimes it is easier just to start again if the model gets in a loop of not being able to fix simple errors (I kept getting syntax errors in the HTML which is very poor performance)

This method is a bit more manual than the second method I will give, but it is easier to tweak and incorporate you own code. 


### Attempt 2: Using Reflux.dev

The website [build.reflux.dev](https://build.reflex.dev/) can be used for vibe-coding a Python web app with a nice interface. The application allows you to prompt a model to create a full web app based on the python `reflex` library. I had not heard of reflex before, but was keen to try out the vibe coding tool. I only used the free plan, which may have been my downfall here, but I am going to describe how I used this free service to create a front end web application. 

I prompted the app with the following:

    Lets create a web application for a chat bot front end. The chatbot is provided in the file below named patient_history_chatbot.py and the connection to the database is given by the other file I am providing, get_iris_connection.py. I want a minimal chatbot interface. The app should:
    - Allow the user to input a patient ID and a prompt
    - Call bot.set_patient_id(patient_id) then run bot.run(user_prompt) to get the response
    - Display the chatbots response on the page
    - Include a `Reset chat` button
    - Keep the design minimal and functional.

I then pasted in the contents of the patient_history_chatbot.py and get_iris_connection.py files.

The response took a couple of minutes, but did create a chatbot interface. But there were a few issues, primarily that it failed to install one of the dependancies. It fixed this by creating a 'mock chatbot' which outwardly acted in the same way as the real chatbot, but didn't actually search the database or probe the model. 

Fixing this from inside reflex seemed impossible, but you can share the code to your github. You have to connect and give it access to a repository (I created an empty repository so it couldn't access all my code). I then could then push the app from reflex.dev straight to my github page. 

Then I cloned the repository to a local directory, swapped the reflex generated chatbot file for my chatbot file, and then opened the terminal in the repo directory and ran: 

`reflex init`

then

`reflex run`

I had a couple of small bugs to fit, but this worked absolutely fine to get it running locally. 

#### Method Evaluation

I much prefered the first method I showed. For clarity, I am writing this as someone who enjoys coding their own apps from scratch, so my opinions are likely to differ from those who lack the knowledge and skills to do this.

My main problem with this method was that without paying for Reflex premium, you can't directly edit the code, so you have to trust the LLM to make the changes required. This trust can be painful when you can see a simple error but cannot fix it directly. 

I guess the bigger problem with the app was that it failed to install one of my dependancies (Sentence Transformers). Had it been able to install all the dependancies needed, it would have been able to run on the wen, although the backend (iris database and Ollama app) would have only been available on my machine.

Another problem with using reflex (whether creating locally or vibe-coding) creates hundreds of files, as the python code is actually just a specification for creating a front end with React. Looking at these files, even as someone who is somewhat familiar with React apps, I have no idea where the back-end is routed to the front end. To compare the flask app runs with 3 files, you do need to create a bit of JavaScript, but LLMs are pretty reliable at doing this. 

On the other hand, if the Python portion of the app could have been deployed on Build.Reflux.Dev (i.e. didn't have any problems with installing dependencies), it is a way to rapidly create a web app that can be deployed to the web without any required knowledge of how to do so. That's a pretty big benefit! 


### Vibe-coding a Python chatbot conclusion

As much as I might have made both of these methods sound very technical and an absolute nightmare, the reality is that within a couple of attempts, and maybe an hour effort maximum, I created working UIs using only prompting (+ a tiny bit of tinkering). 

If you are interested in making a Python web-application with one of these tools, I would start with https://build.reflex.dev, unless:
-  you are using anything that depends on pytorch (like sentence transformers), or anything else that gives you errors saying it can't install the dependencies.
- You have some knowledge of how to create web applications, if so I think using chatGPT is easier, although reflex's automatic deployment is helpful. 