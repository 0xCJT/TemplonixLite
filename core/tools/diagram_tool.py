#########################################################################################
# DiagramTool: Uses the Eraser.io API to create diagrams.
#########################################################################################
import os
import logging
import requests
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env file
load_dotenv()


class DiagramTool:
    #########################################################################################
    # Initialize the tool with a logger and settings.
    #########################################################################################
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
                
        # Load environment variables directly
        self.eraser_api_key: str = os.getenv("ERASER_API_KEY")
        self.eraser_api_url: str = os.getenv("ERASER_API_URL")
        
        # Validate required environment variables
        if not self.eraser_api_key:
            self.logger.error("ERASER_API_KEY environment variable is not set")
            raise ValueError("ERASER_API_KEY environment variable is required")
        
        self.target_folder: str = os.path.abspath("diagrams/")
        os.makedirs(self.target_folder, exist_ok=True)

    #########################################################################################
    # Map diagram types to Eraser API format
    #########################################################################################
    def _map_diagram_type(self, diagram_type: str) -> str:        
        type_mapping = {
            "flowchart": "flowchart-diagram",
            "sequence": "sequence-diagram", 
            "sequence-diagram": "sequence-diagram",
            "cloud": "cloud-architecture-diagram",
            "cloud-architecture": "cloud-architecture-diagram",
            "cloud-architecture-diagram": "cloud-architecture-diagram",
            "er": "entity-relationship-diagram",
            "entity-relationship": "entity-relationship-diagram",
            "entity-relationship-diagram": "entity-relationship-diagram"
        }
        return type_mapping.get(diagram_type.lower(), "flowchart-diagram")

    #########################################################################################
    # Call the Eraser.io API and draw a diagram.
    # diagram_type: sequence-diagram | cloud-architecture-diagram | flowchart-diagram | entity-relationship-diagram
    #########################################################################################
    def draw_diagram(self, instruction: str, filename: str, diagram_type: str) -> str:
        
        eraser_prompt = f"{instruction}"

        # Map the diagram type to Eraser API format
        mapped_type = self._map_diagram_type(diagram_type)
        
        payload = {
            "diagramType": mapped_type,
            "background": False,
            "theme": "light",
            "scale": "1",        
            "text": eraser_prompt,
        }
        
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {self.eraser_api_key}",
        }

        try:
            resp = requests.post(self.eraser_api_url, json=payload, headers=headers, timeout=120)
            resp.raise_for_status()
        except requests.RequestException as e:
            logging.error(f"Eraser drawing request failed: {e}")
            return f"Eraser drawing request failed: {e}"
    
        try:
            data = resp.json()
        except ValueError:
            logging.error("Eraser response was not JSON")
            return "Eraser response was not JSON"

        image_url = data.get("imageUrl")
        if not image_url:
            logging.error(f"Eraser 'imageUrl' missing in response: {data}")
            return f"Eraser 'imageUrl' missing in response: {data}"

        try:
            with requests.get(image_url, stream=True, timeout=120) as r:
                r.raise_for_status()
                file_path = os.path.join(self.target_folder, f"{filename}.png")
                with open(file_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
        except requests.RequestException as e:
            logging.error(f"Failed to download image: {e}")
            return f"Failed to download image: {e}"

        logging.info(f"Diagram saved successfully at {file_path}")
        return file_path