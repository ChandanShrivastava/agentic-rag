from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class USPTOKnowledgeGraph:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def create_patent_graph(self, patent_data):
        with self.driver.session() as session:
            session.write_transaction(self._create_graph, patent_data)

    @staticmethod
    def _create_graph(tx, patent):
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

        # Create Examiner
        tx.run("""
            MERGE (e:Examiner {id: $examiner_id})
            SET e += {
                first_name: $examiner_first,
                middle_name: $examiner_middle,
                last_name: $examiner_last
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
        for inventor in patent["inventors"]:
            tx.run("""
                MERGE (inv:Inventor {
                    first_name: $first_name,
                    last_name: $last_name,
                    city: $city,
                    state: $state,
                    country: $country
                })
                WITH inv
                MATCH (p:Patent {application_number: $application_number})
                MERGE (inv)-[:INVENTED]->(p)
            """, **inventor, application_number=patent["application_number"])


# Example usage
if __name__ == "__main__":
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    kg = USPTOKnowledgeGraph(neo4j_uri, neo4j_user, neo4j_password)

    patent = {
        "application_number": "13817165",
        "publication_number": "US20130296823A1-20131107",
        "title": "Intelligent Drug and/or Fluid Delivery System to Optimizing Medical Treatment or Therapy Using Pharmacodynamic and/or Pharamacokinetic Data",
        "decision": "ACCEPTED",
        "date_produced": "20131024",
        "date_published": "20131107",
        "main_cpc_label": "A61M51723",
        "cpc_labels": ["A61M51723"],
        "main_ipcr_label": "A61M5172",
        "ipcr_labels": ["A61M5172"],
        "patent_number": "9950112",
        "filing_date": "20180219",
        "patent_issue_date": "20180424",
        "abandon_date": None,
        "uspc_class": "604",
        "uspc_subclass": "503000",
        "examiner_id": "74715.0",
        "examiner_last": "HALL",
        "examiner_first": "DEANNA",
        "examiner_middle": "",
        "inventors": [
            {"first_name": "Richard J.", "last_name": "Melker", "city": "Gainesville", "state": "FL", "country": "US"},
            {"first_name": "Donn M.", "last_name": "Dennis", "city": "Gainesville", "state": "FL", "country": "US"},
            {"first_name": "Jeremy", "last_name": "Melker", "city": "Gainesville", "state": "FL", "country": "US"},
            {"first_name": "Mark", "last_name": "Rice", "city": "Jacksonville", "state": "FL", "country": "US"},
            {"first_name": "Robert", "last_name": "Hurley", "city": "Gainesville", "state": "FL", "country": "US"},
        ],
        "abstract": "A pharmacodynamic (PD)...",
        "summary": "SUMMARY OF THE INVENTION The system..."
    }

    kg.create_patent_graph(patent)
    kg.close()
