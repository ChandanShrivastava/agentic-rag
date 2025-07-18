from neo4j import GraphDatabase
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from .jina_embedding import get_jina_embeddings_for_text_chunks
from typing import Dict, Any, List, Optional
from .jina_embedding import model, tokenizer
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Load environment variables
load_dotenv()

class USPTOKnowledgeGraph:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def create_patent_graph(self, patent_data: Dict[str, Any], text_chunks: Optional[List[Dict[str, Any]]] = None):
        with self.driver.session() as session:
            session.write_transaction(self._create_graph, patent_data, text_chunks or [])

    @staticmethod
    def _create_graph(tx, patent: Dict[str, Any], text_chunks: List[Dict[str, Any]]):
        # Create Patent Node
        tx.run("""
            MERGE (p:Patent {application_number: $application_number})
            SET p += {
                publication_number: $publication_number,
                title: $title,
                decision: $decision,
                date_produced: $date_produced,
                date_published: $date_published,
                patent_number: $patent_number,
                filing_date: $filing_date,
                patent_issue_date: $patent_issue_date,
                abandon_date: $abandon_date,
                uspc_class: $uspc_class,
                uspc_subclass: $uspc_subclass,
                abstract: $abstract,
                summary: $summary
            }
        """, **patent)

        # Group by decision outcome
        if patent.get("decision"):
            tx.run("""
                MERGE (d:DecisionGroup {label: $decision})
                WITH d
                MATCH (p:Patent {application_number: $application_number})
                MERGE (p)-[:HAS_DECISION]->(d)
            """, decision=patent["decision"], application_number=patent["application_number"])
            
        # Create Examiner
        tx.run("""
            MERGE (e:Examiner {id: $examiner_id})
            SET e += {
                first_name: $examiner_name_first,
                middle_name: $examiner_name_middle,
                last_name: $examiner_name_last
            }
            WITH e
            MATCH (p:Patent {application_number: $application_number})
            MERGE (e)-[:EXAMINED]->(p)
        """, **patent)

        # Create CPC labels
        for cpc in patent["cpc_labels"]:
            tx.run("""
                MERGE (c:CPC {label: $label})
                WITH c
                MATCH (p:Patent {application_number: $application_number})
                MERGE (p)-[:HAS_CPC]->(c)
            """, label=cpc, application_number=patent["application_number"])

        # Create IPCR labels
        for ipcr in patent["ipcr_labels"]:
            tx.run("""
                MERGE (i:IPCR {label: $label})
                WITH i
                MATCH (p:Patent {application_number: $application_number})
                MERGE (p)-[:HAS_IPCR]->(i)
            """, label=ipcr, application_number=patent["application_number"])

        # Create Inventors
        for inventor in patent["inventor_list"]:
            tx.run("""
                MERGE (inv:Inventor {
                    first_name: $inventor_name_first,
                    last_name: $inventor_name_last,
                    city: $inventor_city,
                    state: $inventor_state,
                    country: $inventor_country
                })
                WITH inv
                MATCH (p:Patent {application_number: $application_number})
                MERGE (inv)-[:INVENTED]->(p)
            """, **inventor, application_number=patent["application_number"])
            
        # Add embedded text chunks as Evidence nodes
        for chunk in text_chunks:
            tx.run("""
                CREATE (e:Evidence {
                    chunk_id: $chunk_id,
                    content: $content,
                    embedding: $embedding,
                    source: $source,
                    created_at: $created_at
                })
                WITH e
                MATCH (p:Patent {application_number: $application_number})
                MERGE (e)-[:EVIDENCE_OF]->(p)
            """,
            chunk_id=chunk["id"],
            content=chunk["content"],
            embedding=chunk["embedding"],
            source=chunk.get("source", ""),
            created_at=chunk.get("created_at", datetime.utcnow().isoformat()),
            application_number=patent["application_number"])

input_path = os.path.abspath("hupd_extracted/2018")
max_files_to_process = 99999999
processed_count = 0

def find_similar_evidence(self, application_number: str, top_k: int = 5) -> List[Dict[str, Any]]:
    query = """
    MATCH (p:Patent {application_number: $app_number})<-[:EVIDENCE_OF]-(source_evidence:Evidence)
    WITH source_evidence.embedding AS query_embedding
    CALL db.index.vector.queryNodes(
      'evidence_embedding_index',
      query_embedding,
      $top_k
    ) YIELD node, score
    RETURN node.chunk_id AS chunk_id, node.content AS content, score
    ORDER BY score DESC
    """
    with self.driver.session() as session:
        result = session.run(query, app_number=application_number, top_k=top_k)
        return [record.data() for record in result]

# Example usage
if __name__ == "__main__":
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    #print(f"Connecting to Neo4j at {neo4j_uri} with user {neo4j_user}  {neo4j_password}")
    if not neo4j_password:
        print("Warning: NEO4J_PASSWORD is not set. Ensure you have the correct password for Neo4j.")    
    kg = USPTOKnowledgeGraph(neo4j_uri, neo4j_user, neo4j_password)

    print(f"Processing JSON files from: {input_path}")
    print(f"Maximum files to process: {max_files_to_process}")
    
    try:
        # List all files in the input folder
        files = [f for f in os.listdir(input_path) if f.endswith('.json')]
        files.sort() # Ensure consistent order for processing

        for filename in files:
            if processed_count >= max_files_to_process:
                print(f"Reached maximum file limit of {max_files_to_process}. Stopping.")
                break

            json_filepath = os.path.join(input_path, filename)

            print(f"Attempting to process '{filename}'...")

            try:
                with open(json_filepath, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)

                # Check the 'abstract' field
                abstract = json_data.get('abstract', None)
                summary = json_data.get('summary', None)
                patent = json_data
                    # Example chunks (embedded using Ollama or OpenAI)
                embeddings = get_jina_embeddings_for_text_chunks(
                    long_text=summary,
                    chunk_size_tokens=500,
                    chunk_overlap_tokens=50,
                    output_dimensionality=None,
                    prompt_name="document",
                    show_progress=True
                )
                embeddingsabstract = get_jina_embeddings_for_text_chunks(
                    long_text=abstract,
                    chunk_size_tokens=500,
                    chunk_overlap_tokens=50,
                    output_dimensionality=None,
                    prompt_name="query",
                    show_progress=True
                )
                
                # Get the text chunks for abstract and summary
                splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
                    tokenizer=tokenizer,
                    chunk_size=500,
                    chunk_overlap=50,
                    add_start_index=True,
                )

                abstract_chunks = splitter.split_text(abstract) if abstract else []
                summary_chunks = splitter.split_text(summary) if summary else []

                # Combine embeddings from abstract and summary into embedded_chunks
                embedded_chunks = []
                for idx, emb in enumerate(embeddingsabstract):
                    embedded_chunks.append({
                        "id": f"abstract_chunk_{idx+1:03d}",
                        "content": abstract_chunks[idx] if idx < len(abstract_chunks) else "",
                        "embedding": emb,
                        "source": "abstract",
                        "created_at": datetime.utcnow().isoformat()
                    })
                for idx, emb in enumerate(embeddings):
                    embedded_chunks.append({
                        "id": f"summary_chunk_{idx+1:03d}",
                        "content": summary_chunks[idx] if idx < len(summary_chunks) else "",
                        "embedding": emb,
                        "source": "summary",
                        "created_at": datetime.utcnow().isoformat()
                    })
                # Create the patent graph in Neo4j
                kg.create_patent_graph(patent, embedded_chunks)
                processed_count += 1
                print(f"Successfully converted '{filename}' to stored in Neo4j.")
            except json.JSONDecodeError:
                print(f"Error: Could not decode JSON from '{filename}'. Skipping.")
            except FileNotFoundError:
                print(f"Error: File '{filename}' not found. Skipping.")
            except Exception as e:
                print(f"An unexpected error occurred while processing '{filename}': {e}. Skipping.")
            processed_count += 1
    except FileNotFoundError:
        print(f"Error: Input folder '{input_path}' not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    print(f"\nFinished processing. Converted {processed_count} JSON files to Neo4j graph nodes.")
        
    kg.close()
