# FHIR + AI Chatbot

## Introduction

In this tutorial, I will go through how FHIR data can be combined with IRIS vector search capabilities to build a powerful tool for medical professionals wanting to quickly understand the medical history of a patient. 

We are going to take the data from 'DocumentReference' resources, these consist of clinical notes attached in plain text. This plain text is encoded within the resource and will need to be decoded.

This tutorial is based on a [demo created by Simon Sha](https://community.intersystems.com/post/demo-video-fhir-powered-ai-healthcare-assistant) for the 2025 InterSystems Demo Games. His demonstration is shown here: 

[![IMAGE ALT TEXT HERE](https://img.youtube.com/vi/P5JcdjLNvbc/0.jpg)](https://www.youtube.com/watch?v=P5JcdjLNvbc)


## Tutorial

This is a start-to-finish tutorial which goes through 

The process shown within this tutorial: 

#### 0-Setup
1. Create instance of IRIS-health and FHIR server
2. Load Data into FHIR Server

#### 1-Create SQL projection
1. Use the IRIS FHIR-SQL builder to create a SQL table from the FHIR data
2. Query this SQL table from Python

#### 2-Create Vector Database
1. Fetch data using SQL queries.
2. Decode Clinical Notes to plain text
3. Use a text-embedding model to encode the Clinical Notes to Vectors
4. Create a new table in IRIS with these Vectors

#### 3-Vector Search
1. Convert a user query into Vectors
2. Perform a rapid Vector search to find related notes

#### 4-Prompt LLM 
1. Create a prompt that includes system instructions,  relevant notes, and a user query
2. Pass prompt to a Large Language Model
3. Return output to user