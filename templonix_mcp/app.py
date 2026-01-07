#########################################################################################
# Templonix Lite Production MCP Server
# Complete server with workflows, memory, knowledge, email, calendar, diagram tools
#########################################################################################
import os
import sys
import logging
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from typing import Any, Dict
from mcp.server.fastmcp import FastMCP
from infra.memory.faiss_memory_manager import SimpleFAISSMemory
from infra.memory.knowledge_loader import KnowledgeLoader

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastMCP("templonix-lite")

# Initialize memory once at startup
logger.info("Initializing FAISS memory...")
memory_store = SimpleFAISSMemory(
    db_path=os.getenv("FAISS_DB_PATH"),
    embedding_model=os.getenv("LOCAL_EMBEDDING_MODEL"),
    max_results=int(os.getenv("MAX_MEMORY_RESULTS", "5"))
)

# Initialize knowledge loader
logger.info("Initializing Knowledge Loader...")
knowledge_loader = KnowledgeLoader(
    memory_manager=memory_store,
    knowledge_dir=os.getenv("KNOWLEDGE_DIR", "knowledge/"),
    chunk_size=int(os.getenv("KNOWLEDGE_CHUNK_SIZE", "1000")),
    chunk_overlap=int(os.getenv("KNOWLEDGE_CHUNK_OVERLAP", "200"))
)

#########################################################################################
# WORKFLOW TOOLS (Core Innovation)
#########################################################################################
@app.tool()
def jina_search(url: str) -> str:
    """Use this to search the web, scrape pages and avoid being denied by proxy servers. Make sure to remember a lot of formatting comes back with the results, so be lazer focussed on extracting the critical context based on the query."""
    cJINA_API_KEY = os.getenv("JINA_API_KEY") 

    jina_url = f"https://r.jina.ai/{url}"
    headers = {'Authorization': f'Bearer {cJINA_API_KEY}', 'X-Return-Format': 'text'}
    response = requests.get(jina_url, headers=headers)

    if response.status_code == 200:
        return response.text
    else:        
        return "There was an error with the page scrape." 

@app.tool()
def workflow_list() -> str:
    """Show available specialized AI workflows and expertise modes. Use when user wants to see what specialized capabilities are available."""
    workflows_dir = Path(__file__).parent.parent / "workflows"
    
    if not workflows_dir.exists():
        return "Error: No workflows directory found."
    
    workflows = []
    for item in workflows_dir.iterdir():
        if item.is_dir() and (item / "prompt.txt").exists():
            try:
                with open(item / "prompt.txt", 'r', encoding='utf-8') as f:
                    content = f.read()
                    first_line = content.split('\n')[0].strip('# ')
                    workflows.append(f"{first_line}")
            except:
                workflows.append(f"**{item.name}**: Available")
    
    if not workflows:
        return "Error: No workflows found."
    
    the_answer = f"""
            # Available Templonix Lite Workflows
            {chr(10).join(workflows)}
            # ----------------------------------------------------------"""
        
    return the_answer

@app.tool()
def workflow_get(workflow_name: str) -> str:
    """Load specialized AI expertise and workflows. Use when user wants to activate specific professional modes like sales negotiation, research, or other specialized capabilities."""
    if not workflow_name:
        return "Error: workflow_name is required"
    
    workflows_dir = Path(__file__).parent.parent / "workflows"
    workflow_path = workflows_dir / workflow_name / "prompt.txt"
    
    if not workflow_path.exists():
        available_workflows = []
        if workflows_dir.exists():
            for item in workflows_dir.iterdir():
                if item.is_dir() and (item / "prompt.txt").exists():
                    available_workflows.append(item.name)
        
        available_text = f"Available: {', '.join(available_workflows)}" if available_workflows else "None available"
        return f"Error: Workflow '{workflow_name}' not found. {available_text}"
    
    try:
        with open(workflow_path, 'r', encoding='utf-8') as f:
            prompt_content = f.read()
        
        workflow_title = workflow_name.replace('_', ' ').title()
        
        the_answer = f"""
            # Workflow Loaded: {workflow_title}
            {prompt_content}
            -------------------------------------------------------------------------------------------------
            **Workflow successfully loaded!** You are now operating as a specialized {workflow_title} expert.
            You have gained access to:
            - Domain-specific knowledge and expertise
            - Proven techniques and best practices  
            - Strategic frameworks and tactical approaches
            - Professional language patterns and methodologies
            -------------------------------------------------------------------------------------------------
            Feel free to ask me anything related to {workflow_title.lower()} - I'm now equipped with specialized expertise in this area!"""
    
        return the_answer
    
    except Exception as e:
        logger.error(f"Error reading workflow '{workflow_name}': {e}")
        return f"Error reading workflow '{workflow_name}': {str(e)}"

#########################################################################################
# KNOWLEDGE TOOLS (Document Ingestion & Retrieval)
#########################################################################################
@app.tool()
def knowledge_load(force_reload: bool = False) -> str:
    """Process and embed documents from the local /knowledge folder into the vector store. Use this when the user has added new documents to their knowledge folder and wants to make them searchable. Set force_reload=True to reprocess all files regardless of whether they've changed."""
    try:
        summary = knowledge_loader.load_and_process_documents(force_reload)
        
        result = "Knowledge Base Update Complete\n"
        result += "=" * 40 + "\n\n"
        result += f"Files discovered: {summary['files_discovered']}\n"
        result += f"Files processed: {summary['files_processed']}\n"
        result += f"Files skipped (unchanged): {summary['files_skipped']}\n"
        result += f"Chunks created: {summary['chunks_created']}\n"
        
        if summary['processed_files']:
            result += f"\nProcessed files:\n"
            for filename in summary['processed_files']:
                result += f"  - {filename}\n"
        
        if summary['errors']:
            result += f"\nErrors encountered:\n"
            for error in summary['errors']:
                result += f"  - {error}\n"
        
        return result
        
    except Exception as e:
        logger.error(f"Error loading knowledge: {e}")
        return f"Error updating knowledge base: {str(e)}"


@app.tool()
def knowledge_search(query: str, limit: int = 5) -> str:
    """Search the knowledge base for information from ingested documents. Use this when the user asks questions that might be answered by their personal documents in the knowledge folder. This searches ONLY the knowledge namespace, not conversational memories."""
    try:
        results = memory_store.search_memory(
            query=query,
            namespace="knowledge",
            limit=limit
        )
        
        if not results:
            return f"No knowledge found matching: {query}\n\nTip: Make sure documents have been loaded using the knowledge_load tool."
        
        formatted_results = []
        for i, result in enumerate(results, 1):
            content = result.get("content", "")
            score = result.get("score", 0)
            metadata = result.get("metadata", {})
            source = metadata.get("source_file", "Unknown")
            chunk_idx = metadata.get("chunk_index", "?")
            total_chunks = metadata.get("total_chunks", "?")
            
            # Truncate content for display if very long
            display_content = content if len(content) <= 800 else content[:800] + "..."
            
            formatted_results.append(
                f"[{i}] Source: {source} (chunk {chunk_idx}/{total_chunks})\n"
                f"    Relevance: {score:.3f}\n"
                f"    Content:\n    {display_content}\n"
            )
        
        header = f"Found {len(results)} relevant knowledge entries:\n"
        header += "=" * 50 + "\n\n"
        
        return header + "\n".join(formatted_results)
        
    except Exception as e:
        logger.error(f"Error searching knowledge: {e}")
        return f"Error searching knowledge base: {str(e)}"


@app.tool()
def knowledge_stats() -> str:
    """Get statistics about the knowledge base, including processed files, chunk counts, and storage details."""
    try:
        stats = knowledge_loader.get_knowledge_stats()
        memory_stats = memory_store.get_stats()
        
        result = "Knowledge Base Statistics\n"
        result += "=" * 40 + "\n\n"
        result += f"Knowledge directory: {stats['knowledge_dir']}\n"
        result += f"Supported formats: {', '.join(stats['supported_formats'])}\n\n"
        
        result += f"Total files processed: {stats['files_processed']}\n"
        result += f"Total chunks in store: {memory_stats['knowledge_count']}\n"
        result += f"Total characters indexed: {stats['total_characters']:,}\n\n"
        
        processed = stats.get('processed_files', {})
        if processed:
            result += "Processed Files:\n"
            result += "-" * 30 + "\n"
            for filename, info in processed.items():
                result += f"  {filename}\n"
                result += f"    Chunks: {info['chunks']} | Characters: {info.get('char_count', 'N/A'):,}\n"
                result += f"    Processed: {info['processed_at']}\n"
        else:
            result += "No files have been processed yet.\n"
            result += "Add documents to the knowledge folder and run knowledge_load.\n"
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting knowledge stats: {e}")
        return f"Error getting knowledge stats: {str(e)}"


@app.tool()
def knowledge_clear(confirm: bool = False) -> str:
    """DESTRUCTIVE: Clear all knowledge from the vector store. This removes all ingested documents but does not delete the original files. Set confirm=True to proceed."""
    try:
        result = knowledge_loader.clear_knowledge(confirm)
        return result
    except Exception as e:
        logger.error(f"Error clearing knowledge: {e}")
        return f"Error clearing knowledge: {str(e)}"


#########################################################################################
# MEMORY TOOLS (Conversational Memory - Local FAISS)
#########################################################################################
@app.tool()
async def archive_insert(
    content: str,
    session_id: str = "default"
) -> str:
    """Remember and store information permanently in your local memory. Use this when user says 'remember this', 'save this', or wants to store important information for later recall. This stores in the MEMORY namespace, separate from knowledge documents."""
    try:
        if not content:
            return "Error: Content is required"
        
        # Store in memory namespace with session tracking
        memory_id = memory_store.add_memory(
            content=content,
            namespace="memory",
            session_id=session_id
        )
        logger.info(f"Stored memory {memory_id}")
        
        return f"Memory stored successfully with ID: {memory_id}"
        
    except Exception as e:
        logger.error(f"Error storing memory: {e}")
        return f"Error storing memory: {str(e)}"


@app.tool()
async def archive_search(
    query: str,
    session_id: str = "default",
    limit: int = 5,
) -> str:
    """Search your memory for previously stored information. Use when user asks 'what did I tell you about X', 'do you remember X', or needs to recall past conversations. This searches ONLY conversational memories, not knowledge documents."""
    try:
        if not query:
            return "Error: Query is required"
        
        results = memory_store.search_memory(
            query=query,
            namespace="memory",
            limit=limit
        )
        
        if not results:
            return f"No memories found for query: {query}"
        
        formatted_results = []
        
        for i, result in enumerate(results, 1):
            content = result.get("content", "")
            score = result.get("score", 0)
            timestamp = result.get("timestamp", "Unknown")
            
            formatted_results.append(
                f"{i}. {content}\n"
                f"   Relevance: {score:.2f} | Stored: {timestamp}"
            )
        
        return f"Found {len(results)} memories:\n\n" + "\n\n".join(formatted_results)
        
    except Exception as e:
        logger.error(f"Error searching memory: {e}")
        return f"Error searching memory: {str(e)}"


@app.tool()
async def archive_search_all(
    query: str,
    limit: int = 10
) -> str:
    """Search across BOTH knowledge documents AND conversational memories. Use this when the user's question might be answered by either source, when you need a comprehensive view, or when you're unsure which namespace contains the relevant information. Results are clearly labelled by source type."""
    try:
        if not query:
            return "Error: Query is required"
        
        results = memory_store.search_all(
            query=query,
            limit=limit
        )
        
        if not results:
            return f"No results found for query: {query}\n\nTip: Try loading knowledge documents or storing memories first."
        
        # Count by source type
        knowledge_count = sum(1 for r in results if r.get("source_type") == "KNOWLEDGE")
        memory_count = sum(1 for r in results if r.get("source_type") == "MEMORY")
        
        formatted_results = []
        
        for i, result in enumerate(results, 1):
            content = result.get("content", "")
            score = result.get("score", 0)
            source_type = result.get("source_type", "UNKNOWN")
            timestamp = result.get("timestamp", "Unknown")
            metadata = result.get("metadata", {})
            
            # Truncate content for display
            display_content = content if len(content) <= 600 else content[:600] + "..."
            
            # Format based on source type
            if source_type == "KNOWLEDGE":
                source_file = metadata.get("source_file", "Unknown")
                chunk_idx = metadata.get("chunk_index", "?")
                formatted_results.append(
                    f"[{i}] [{source_type}] Source: {source_file} (chunk {chunk_idx})\n"
                    f"    Relevance: {score:.3f}\n"
                    f"    {display_content}\n"
                )
            else:
                formatted_results.append(
                    f"[{i}] [{source_type}] Stored: {timestamp}\n"
                    f"    Relevance: {score:.3f}\n"
                    f"    {display_content}\n"
                )
        
        header = f"Found {len(results)} results ({knowledge_count} from knowledge, {memory_count} from memory):\n"
        header += "=" * 60 + "\n\n"
        
        return header + "\n".join(formatted_results)
        
    except Exception as e:
        logger.error(f"Error in unified search: {e}")
        return f"Error searching: {str(e)}"


@app.tool()
def archive_purge(
    session_id: str = None,
    confirm: bool = False
) -> str:
    """**DESTRUCTIVE**: Permanently delete memories from the vector store. Only affects conversational memories, not knowledge documents. Set confirm=True to execute."""
    try:
        if not confirm:
            return "Purge cancelled. Set confirm=True to proceed with deletion."
        
        count_before = memory_store.get_memory_count("memory")
        
        # Clear only the memory namespace
        memory_store.clear_memories(namespace="memory")
        
        count_after = memory_store.get_memory_count("memory")
        return f"Purged memories. Deleted: {count_before} memories. Remaining: {count_after}"
        
    except Exception as e:
        logger.error(f"Error purging memories: {e}")
        return f"Error purging memories: {str(e)}"


@app.tool()
def archive_stats() -> str:
    """Get statistics about the memory and knowledge stores."""
    try:
        stats = memory_store.get_stats()
        
        result = "Memory Store Statistics\n"
        result += "=" * 40 + "\n\n"
        result += f"Total entries: {stats['total_entries']}\n"
        result += f"  - Memories: {stats['memory_count']}\n"
        result += f"  - Knowledge: {stats['knowledge_count']}\n\n"
        result += f"By Tier:\n"
        result += f"  - Sacred: {stats['tier_counts']['Sacred']}\n"
        result += f"  - Active: {stats['tier_counts']['Active']}\n"
        result += f"  - Archival: {stats['tier_counts']['Archival']}\n\n"
        result += f"Database location: {stats['db_path']}\n"
        
        # Check file sizes
        db_path = Path(stats['db_path'])
        index_path = db_path / "faiss_index.bin"
        metadata_path = db_path / "metadata.json"
        docs_path = db_path / "documents.pkl"
        
        if index_path.exists():
            size_mb = index_path.stat().st_size / (1024 * 1024)
            result += f"Index size: {size_mb:.2f} MB\n"
        
        if metadata_path.exists():
            size_kb = metadata_path.stat().st_size / 1024
            result += f"Metadata size: {size_kb:.2f} KB\n"
            
        if docs_path.exists():
            size_kb = docs_path.stat().st_size / 1024
            result += f"Documents size: {size_kb:.2f} KB\n"
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return f"Error getting stats: {str(e)}"

#########################################################################################
# EMAIL TOOLS
#########################################################################################
@app.tool()
async def email_send(
    to: str,
    subject: str,
    body: str,
    attachment_path: str = None
) -> str:
    """Send emails directly through Gmail. Use when user wants to send emails, follow up on meetings, or communicate with contacts."""
    try:
        from core.tools.email_tool import EmailTool
        
        tool = EmailTool()        
        result = tool.send_email(to, subject, body, attachment_path)
        return result
        
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return f"Error sending email: {str(e)}"

@app.tool()
async def email_save_draft(
    to: str,
    subject: str,
    body: str,
    attachment_path: str = None
) -> str:
    """Save an email draft to Gmail. Use before sending, or when you want to review/finish later."""
    try:
        from core.tools.gmail_tool import GmailTool
        tool = GmailTool()
        result = tool.create_draft(to, subject, body, attachment_path)
        return result
    except Exception as e:
        logger.error(f"Email draft failed: {e}")
        return f"Error creating email draft: {str(e)}"

#########################################################################################
# CALENDAR TOOLS
#########################################################################################
@app.tool()
async def calendar_create_event(
    title: str,
    description: str,
    start_datetime: str,
    end_datetime: str,
    attendees: list[str] = None,
    location: str = "",
    send_notifications: bool = True,
    timezone: str = "Europe/London"
) -> str:
    """Schedule meetings and events in Google Calendar. Use when user wants to create meetings, schedule appointments, or block time for tasks.
    
    Args:
        title: Event title
        description: Event description
        start_datetime: Start time in ISO-8601 format (e.g., "2024-01-15T14:30:00+01:00")
        end_datetime: End time in ISO-8601 format (e.g., "2024-01-15T15:30:00+01:00")
        attendees: List of email addresses to invite
        location: Event location
        send_notifications: Whether to send email notifications
        timezone: Timezone for the event (defaults to Europe/London)
    """
    try:
        from core.tools.calendar_tool import CalendarTool
        import os
        
        class SimpleCalendarConfig:
            def __init__(self):
                self.GOOGLE_CALENDAR_CREDENTIALS_PATH = os.getenv("GOOGLE_CALENDAR_CREDENTIALS_PATH", "credentials.json")
                self.GOOGLE_CALENDAR_TOKEN_PATH = os.getenv("GOOGLE_CALENDAR_TOKEN_PATH", "token.json")
        
        config = SimpleCalendarConfig()
        tool = CalendarTool(config)
        
        event_id = tool.create_event(
            title=title,
            description=description,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            attendees=attendees or [],
            location=location,
            send_notifications=send_notifications,
            timezone=timezone
        )
        return f"Calendar event created successfully with ID: {event_id}"
        
    except Exception as e:
        logger.error(f"Calendar create failed: {e}")
        return f"Error creating calendar event: {str(e)}"


@app.tool()
async def calendar_list_events(max_results: int = 10) -> str:
    """Check your upcoming schedule and events. Use when user asks 'what's on my calendar', 'what meetings do I have', or needs to see their schedule."""
    try:
        from core.tools.calendar_tool import CalendarTool
        import os
        
        class SimpleCalendarConfig:
            def __init__(self):
                self.GOOGLE_CALENDAR_CREDENTIALS_PATH = os.getenv("GOOGLE_CALENDAR_CREDENTIALS_PATH", "credentials.json")
                self.GOOGLE_CALENDAR_TOKEN_PATH = os.getenv("GOOGLE_CALENDAR_TOKEN_PATH", "token.json")
        
        config = SimpleCalendarConfig()
        tool = CalendarTool(config)
        
        events = tool.list_upcoming_events(max_results)
        return f"Upcoming events:\n\n{events}"
        
    except Exception as e:
        logger.error(f"Calendar list failed: {e}")
        return f"Error listing calendar events: {str(e)}"


@app.tool()
async def calendar_delete_event(event_id: str) -> str:
    """Cancel or delete calendar events. Use when user wants to cancel meetings or remove events from their schedule."""
    try:
        from core.tools.calendar_tool import CalendarTool
        import os
        
        class SimpleCalendarConfig:
            def __init__(self):
                self.GOOGLE_CALENDAR_CREDENTIALS_PATH = os.getenv("GOOGLE_CALENDAR_CREDENTIALS_PATH", "credentials.json")
                self.GOOGLE_CALENDAR_TOKEN_PATH = os.getenv("GOOGLE_CALENDAR_TOKEN_PATH", "token.json")
        
        config = SimpleCalendarConfig()
        tool = CalendarTool(config)
        
        tool.delete_event(event_id)
        return f"Calendar event {event_id} deleted successfully"
        
    except Exception as e:
        logger.error(f"Calendar delete failed: {e}")
        return f"Error deleting calendar event: {str(e)}"


#########################################################################################
# DIAGRAM TOOLS
#########################################################################################
@app.tool()
async def diagram_create(
    instruction: str,
    filename: str,
    diagram_type: str = "flowchart"
) -> str:
    """Create professional diagrams using Eraser.io. Use when user mentions /eraser, 'eraser', 'create a diagram with eraser', or when complex information would benefit from visual representation. Supports ONLY: flowchart, sequence-diagram, cloud-architecture-diagram, entity-relationship-diagram."""
    try:        
        from core.tools.diagram_tool import DiagramTool
        tool = DiagramTool()                
        result = tool.draw_diagram(instruction, filename, diagram_type)
        return f"Diagram created successfully: {result}"
        
    except Exception as e:
        logger.error(f"Diagram create failed: {e}")
        return f"Error creating diagram: {str(e)}"


if __name__ == "__main__":    
    logger.info("Starting Templonix Lite Production MCP Server")
    logger.info("All tools initialized and ready")
    try:
        app.run(transport="stdio")
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Server error: {e}")
        sys.exit(1)