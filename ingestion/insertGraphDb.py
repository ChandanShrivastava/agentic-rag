from langchain_core.documents import Document
from langchain_core.graph import GraphDocument, Node, Relationship
from neo4j import GraphDatabase


def __init__(self, uri, user, password):
    self.driver = GraphDatabase.driver(uri, auth=(user, password))
        
def add_graphdocument_to_neo4j(
    graph_doc: GraphDocument,
    uri: str,
    user: str,
    password: str,
    database: Optional[str] = "neo4j"
):
    
    
    def add_graph(tx, graph_doc: GraphDocument):
        # Create nodes
        for node in graph_doc.nodes:
            tx.run(
                f"""
                MERGE (n:{node.type} {{id: $id}})
                SET n += $properties
                """,
                id=node.id,
                properties=node.properties
            )
        
        # Create relationships
        for rel in graph_doc.relationships:
            tx.run(
                f"""
                MATCH (source:{rel.source.type} {{id: $source_id}})
                MATCH (target:{rel.target.type} {{id: $target_id}})
                MERGE (source)-[r:{rel.type}]->(target)
                SET r += $properties
                """,
                source_id=rel.source.id,
                target_id=rel.target.id,
                properties=rel.properties
            )

        # Optionally store document metadata
        doc_id = str(uuid4())
        tx.run(
            """
            MERGE (d:Document {id: $doc_id})
            SET d.content = $content,
                d.metadata = $metadata
            """,
            doc_id=doc_id,
            content=graph_doc.source.page_content,
            metadata=graph_doc.source.metadata
        )

        # Optionally relate document to nodes
        for node in graph_doc.nodes:
            tx.run(
                """
                MATCH (d:Document {id: $doc_id})
                MATCH (n {id: $node_id})
                MERGE (d)-[:MENTIONS]->(n)
                """,
                doc_id=doc_id,
                node_id=node.id
            )

    # Run transaction
    with driver.session(database=database) as session:
        session.write_transaction(add_graph, graph_doc)

    driver.close()


def main():
    # Create source document
    doc = Document(
        page_content="Einstein developed the theory of relativity.",
        metadata={"source": "Wikipedia"}
    )

    # Create nodes
    einstein = Node(id="einstein", type="Person", properties={"name": "Albert Einstein"})
    relativity = Node(id="relativity", type="Theory", properties={"name": "Theory of Relativity"})

    # Create relationship
    developed = Relationship(
        source=einstein,
        target=relativity,
        type="DEVELOPED",
        properties={"year": 1905}
    )

    # Create graph document
    graph_doc = GraphDocument(
        nodes=[einstein, relativity],
        relationships=[developed],
        source=doc
    )

    # Upload to Neo4j
    add_graphdocument_to_neo4j(
        graph_doc,
        uri="bolt://localhost:7687",
        user="neo4j",
        password="your_password_here"
    )


if __name__ == "__main__":
    main()