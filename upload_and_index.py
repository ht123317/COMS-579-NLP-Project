import argparse
import fitz  # PyMuPDF
import re
import pinecone
import os

from dotenv import load_dotenv, find_dotenv
from pinecone import Pinecone
from transformers import AutoTokenizer, AutoModel
import torch
import numpy as np

# Initialize tokenizer and model
tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
model = AutoModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
load_dotenv(find_dotenv())
# def embed_text(chunk):
#
#     # Tokenize the text chunk
#     inputs = tokenizer(chunk, return_tensors="pt", padding=True, truncation=True, max_length=512)
#
#     # Move the tensors to the same device as the model
#     inputs = {name: tensor.to(model.device) for name, tensor in inputs.items()}
#
#     # Generate embeddings
#     with torch.no_grad():
#         outputs = model(**inputs)
#
#     # Pool the outputs into a single mean vector
#     embeddings = outputs.last_hidden_state.mean(dim=1)
#
#     # Convert to list and return
#     return embeddings.squeeze().tolist()
def embed_text(chunk):
    from llama_index.embeddings.openai import OpenAIEmbedding
    embed_model = OpenAIEmbedding()
    vector = embed_model.get_text_embedding(chunk)
    return vector



#Initialize pinecone
pc = Pinecone(api_key="93d07fdf-8263-4af9-99e7-1d0a98a4e504")
index = pc.Index("rag-system")

def read_pdf(pdf_path):
    """Reads a PDF and returns its text content."""
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def clean_text(text):
    """Preprocesses the PDF text by removing unwanted elements."""
    cleaned_text = re.sub(r'\bPage \d+\b', '', text)  # Remove 'Page X'
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text)  # Replace multiple spaces with single space
    return cleaned_text

def chunk_text(text, chunk_size=500, overlap=0.25):
    """Chunks text into overlapping pieces."""
    words = text.split()
    chunk_step = int(chunk_size * (1 - overlap))  # Calculate step size based on overlap
    chunks = [' '.join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_step) if i + chunk_size <= len(words)]
    return chunks


def upload_and_index(pdf_path):
    """Processes a PDF file and indexes its content."""
    text = read_pdf(pdf_path)
    cleaned_text = clean_text(text)
    chunks = chunk_text(cleaned_text)
    for i, chunk in enumerate(chunks):
        embedding = embed_text(chunk)
        index.upsert(vectors=[(str(i), embedding, {'text': chunk})])  # Store embedding and text in Pinecone

def query_index(query):
    """Queries the Pinecone index with a user-provided search query."""
    query_embedding = embed_text(query)
    results = index.query(query_embedding, top_k=5, include_metadata=True)
    return [(match['metadata']['text'], match['score']) for match in results['matches']]
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload and index a PDF file.")
    parser.add_argument("--pdf_file", type=str, required=True, help="Path to the PDF file to be uploaded and indexed.")
    
    args = parser.parse_args()
    upload_and_index(args.pdf_file)
    print(f"Successfully processed and indexed {args.pdf_file}.")