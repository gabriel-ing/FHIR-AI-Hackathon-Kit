# Using IRIS with Python for FHIR and AI applications

This repository contains tutorials for how to use InterSystems IRIS with an external Python Application to combine FHIR data with generative AI methods. 

## Contents 

This repo has 4 main sections: 
- **Tutorial**: contains several markdown and ipython notebook files:
    - How to set up a FHIR server with Docker
    - How to create SQL tables from a FHIR Server with FHIR-SQL Builder
    - Implementing a vector search
    - Creating a chatbot
- **Additional Demos** - Some additional tutorials with other ways to use the IRIS FHIR server with Python. This includes: 
    - Accessing FHIR resources directly
    - Adding data to the FHIR server
    - Generating Synthetic data
    - Links to a demo of Vibe-coding a UI for a FHIR server
- **Resources** - Some brief introductions that may be useful to get started quickly. These include: 
    - What is InterSystems IRIS
    - What is Results augmented generation (RAG)
    - What is FHIR
- **Dockerfhir** - Files to create a local IRIS-health-community instance and FHIR server with Docker. The main tutorial covers how this should be used. 

## Requirements 

- **DOCKER** - The IRIS-health instance and FHIR server in all examples are run in a docker container, for this you will need to install [Docker](https://www.docker.com/)

- **Ollama** - The last step of the main tutorial is to query a local Large Language model, which I have done through Ollama. If you are interested in using a local chatbot, you're best to install Ollama which can be done from their [website](https://ollama.com/).

- **IRIS-Python Driver** - You will also need the InterSystems python driver throughout, this can be installed with pip: `pip install intersystems-irispython`. 
 
- **Other Python Packages** - Various other python packages are used throughout, these are listed in the requirements.txt file and can be installed easily: `pip install -r requirements.txt`. I've stated whenever a new pacakage is used throughout the demos, so if you'd rather only install the packages you need you can skip this and install the remaining packages when you need them.


# FHIR + AI Chatbot Demo

## Introduction

In this tutorial, I will go through how FHIR data can be combined with IRIS vector search capabilities to build a powerful tool for medical professionals wanting to quickly understand the medical history of a patient. 

We are going to take the data from 'DocumentReference' resources, these consist of clinical notes attached in plain text. This plain text is encoded within the resource and will need to be decoded.

This tutorial is based on a [demo created by Simon Sha](https://community.intersystems.com/post/demo-video-fhir-powered-ai-healthcare-assistant) for the 2025 InterSystems Demo Games. His demonstration is shown here: 

[![IMAGE ALT TEXT HERE](https://img.youtube.com/vi/P5JcdjLNvbc/0.jpg)](https://www.youtube.com/watch?v=P5JcdjLNvbc)


## Tutorial

This is a start-to-finish tutorial which goes through:

#### [0 - FHIR server set-up](./Tutorial/0-FHIR-server-setup.md)
1. Create instance of IRIS-health and FHIR server
2. Load Data into FHIR Server

#### [1 - Create SQL projection](./Tutorial/1-Using-FHIR-SQL-Builder.ipynb)
1. Use the IRIS FHIR-SQL builder to create a SQL table from the FHIR data
2. Query this SQL table from Python

#### [2 - Create Vector Database](./Tutorial/2-Creating-Vector-DB.ipynb)
1. Fetch data using SQL queries.
2. Decode Clinical Notes to plain text
3. Use a text-embedding model to encode the Clinical Notes to Vectors
4. Create a new table in IRIS with these Vectors

#### [3 - Vector Search](/Tutorial/3-Vector-Search-LLM-Prompting.ipynb)
1. Convert a user query into Vectors
2. Perform a rapid Vector search to find related notes

#### [3 pt2 - Prompt LLM](/Tutorial/3-Vector-Search-LLM-Prompting.ipynb)
1. Create a prompt that includes system instructions,  relevant notes, and a user query
2. Pass prompt to a Large Language Model
3. Return output to user

## Video Demo

https://github.com/user-attachments/assets/e6d24c52-a4f8-4d73-be62-fa39352515b8


