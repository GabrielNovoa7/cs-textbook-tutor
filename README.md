# CS Textbook Tutor

An AI-powered textbook study application that allows users to upload computer science textbooks, ask questions about the material, continue saved conversations, and study using responses grounded in the uploaded book.

## Project Purpose

This is primarily a learning project.

I am building this application to improve my understanding of full-stack development, backend APIs, databases, retrieval-augmented generation (RAG), vector search, and AI integration.

The finished application is also intended to be something I personally use for studying computer science courses and preparing for exams.

## AI-Assisted Development

This project is being developed with significant AI assistance.

ChatGPT is being used heavily for:

- architecture planning
- code generation
- implementation guidance
- debugging
- explaining unfamiliar concepts
- reviewing code structure
- suggesting improvements
- documentation

Because this is a learning project, I am intentionally working through the code step by step rather than treating the generated code as a finished black box.

My goal is to understand how the system works, test and modify the implementation myself, and become more comfortable with the technologies used throughout the project.

The final integration, testing, project decisions, and continued development are managed by me.

## Current Features

- Upload PDF textbooks
- Extract text from PDF pages
- Preserve textbook page numbers
- Split textbook content into searchable chunks
- Store textbooks and chunks using SQLite
- Detect duplicate textbook uploads
- Create semantic embeddings using ChromaDB
- Search textbook content by meaning
- Generate textbook-grounded explanations using the OpenAI API
- Create persistent study chats
- Save user and assistant messages
- Continue conversations using previous chat history

## Current Architecture

```text
PDF Textbook
     |
     v
PyMuPDF
Text Extraction
     |
     v
Page-Aware Chunking
     |
     +--------------------+
     |                    |
     v                    v
SQLite                ChromaDB
Metadata / Text       Vector Embeddings
     |                    |
     +---------+----------+
               |
               v
        Semantic Search
               |
               v
        Relevant Passages
               |
               v
          OpenAI API
               |
               v
        AI Tutor Response
```
