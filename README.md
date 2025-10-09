# Using IRIS with Python for FHIR and AI applications

This repository contains tutorials for how to use InterSystems IRIS with an external Python Application to combine FHIR data with generative AI methods. 

## Contents 

This repo has 3 main sections: 
- **Tutorial**: contains several markdown and ipython notebook files which show how to set up a FHIR server, create SQL tables and implement a vector search in IRIS. It also contains a basic example of how this can be used to create a RAG chatbot (see video below).
- **Additional Demos** - Some additional tutorials with other ways to use the IRIS FHIR server with Python. For example, it demonstrates a method to create new FHIR resources. These aren't used in the main tutorial sequence, but may be useful to your solutions.
- **Resources** - Some brief introductions that may be useful to get started quickly. These include: 
    - What is InterSystems IRIS
    - What is Results augmented generation (RAG)
    - What is FHIR


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


