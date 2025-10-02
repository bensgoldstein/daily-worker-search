"""
AI-powered Daily Worker Search Database
Copyright (c) 2025 Benjamin Goldstein
Licensed under the MIT License - see LICENSE file for details

How to Use page for the Daily Worker search application.
"""

import streamlit as st
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from auth import AuthManager

# Page configuration
st.set_page_config(
    page_title="How to Use - AI-powered Daily Worker Search",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS (matching main app style)
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .section-header {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #2a5298;
        margin: 1.5rem 0 1rem 0;
    }
    
    .tip-box {
        background-color: #e7f3ff;
        border: 1px solid #b3d9ff;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
</style>
""", unsafe_allow_html=True)

# Initialize auth and require authentication
auth = AuthManager()
auth.require_authentication()

# Header with back navigation
col1, col2 = st.columns([1, 6])
with col1:
    if st.button("← Back to Search"):
        st.switch_page("app.py")

# Header with Daily Worker masthead - matching main app
import base64
from pathlib import Path

# Get the masthead image path
masthead_path = Path(__file__).parent.parent / "ilovepdf_pages-to-jpg" / "per_daily-worker_daily-worker_1935-01-01_12_1_page-0001.jpg"

if masthead_path.exists():
    # Read and encode the local image
    with open(masthead_path, "rb") as img_file:
        img_base64 = base64.b64encode(img_file.read()).decode()
    masthead_img_src = f"data:image/jpeg;base64,{img_base64}"
else:
    # Use Google Drive hosted image for cloud deployment
    gdrive_file_id = "1aFE1IZ9Z3EHs5TTZ8CTJv5vFpWpOU1On"
    masthead_img_src = f"https://drive.google.com/uc?export=view&id={gdrive_file_id}"

st.markdown(f"""
<div class="main-header">
    <div style="display: flex; align-items: center; justify-content: center; gap: 2rem; flex-wrap: wrap;">
        <div style="flex: 1; text-align: center; min-width: 300px;">
            <h1>How to Use the AI-powered Daily Worker Search</h1>
            <p>Complete guide to searching the CPUSA's Daily Worker archive</p>
        </div>
        <div style="flex: 0 0 auto;">
            <img src="{masthead_img_src}" 
                 alt="Daily Worker Masthead from January 1, 1935" 
                 style="max-height: 120px; width: auto; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.2); 
                        object-fit: contain; object-position: top;">
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Getting Started
st.markdown("""
<div class="section-header">
    <h2>Getting Started</h2>
</div>
""", unsafe_allow_html=True)

st.markdown("""
The AI-powered Daily Worker Search Database provides access to **over 9,900 digitized newspaper issues** from the Daily Worker and The Worker, 
spanning **34 years of coverage** from 1924 to 1958. This comprehensive archive captures crucial decades of American labor 
history, social movements, and political developments through the lens of the Communist Party USA's primary publication.

**What You Can Do:**
- Search using natural language questions or specific keywords
- Get AI-powered analysis and synthesis of historical sources
- Export results to PDF or Excel with complete source analysis
- Build conversational searches that build on previous queries
- Access direct links to original newspaper pages on Internet Archive
""")

# Search Methods
st.markdown("""
<div class="section-header">
    <h2>Search Methods</h2>
</div>
""", unsafe_allow_html=True)

st.markdown("""
**The system uses advanced semantic search** that combines AI understanding with keyword matching to find the most relevant results. 
Simply ask questions in natural language - no need to worry about search types or technical settings.

### How to Search
- **Ask complete questions**: "How did the Daily Worker cover the 1935 Wagner Act?"
- **Use natural language**: "What was the paper's stance on Roosevelt's New Deal?"
- **Be conversational**: "How did women's roles in labor organizing change over time?"
- **Follow up**: After one search, ask related questions to build deeper understanding

### Search Examples That Work Well
""")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    **Historical Events**
    - "How did the Daily Worker report on the Stock Market Crash of 1929?"
    - "What was the paper's coverage of the Spanish Civil War?"
    - "How did the Daily Worker discuss World War II before US entry?"
    """)

with col2:
    st.markdown("""
    **Social & Political Issues**
    - "What strategies for union organizing were promoted in the 1930s?"
    - "How did the Daily Worker address racial discrimination?"
    - "What was the paper's relationship with the Socialist Party?"
    """)

# Response Modes
st.markdown("""
<div class="section-header">
    <h2>Response Modes: Essay vs Source Analysis</h2>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.subheader("📝 Essay Generation Mode")
    st.markdown("""
    **Best for comprehensive research questions**
    - AI synthesizes information from multiple sources
    - Provides a cohesive, essay-style answer
    - Sources cited as [Source 1], [Source 2], etc.
    - Great for understanding topics across time
    - **Example output**: A detailed analysis drawing from 5-10 sources
    """)

with col2:
    st.subheader("🔍 Source Analysis Mode")
    st.markdown("""
    **Best for detailed source examination**
    - AI analyzes each source individually
    - Expandable sections for each newspaper source
    - Detailed analysis of how each source relates to your question
    - Perfect for academic research and citation
    - **Excel export available** with complete analysis
    """)

st.markdown("""
<div class="tip-box">
<strong>Excel Export:</strong> In Source Analysis mode, you can download a comprehensive Excel spreadsheet containing 
source numbers, URLs, dates, citations, newspaper names, and the complete AI analysis for each source. Perfect for 
academic research, citation management, and detailed documentation.
</div>
""", unsafe_allow_html=True)

# Search Tips
st.markdown("""
<div class="section-header">
    <h2>Search Tips</h2>
</div>
""", unsafe_allow_html=True)

st.markdown("""
### Effective Search Strategies

**1. Ask Complete Questions**
- Use full sentence questions: "What was the Daily Worker's coverage of the 1935 Wagner Act?"
- Frame queries as research questions: "How did the paper report on women's roles in labor organizing?"
- Be conversational: "What did the Daily Worker think about Roosevelt's economic policies?"

**2. Leverage Historical Context**
- Use period-appropriate terminology and names
- Search for "Great War" instead of "World War I" for 1920s coverage
- Consider how events were understood at the time
- Remember the paper's socialist perspective when framing questions

**3. Build on Previous Searches**
- Use the conversational mode - each search builds on previous context
- Ask follow-up questions: "How did this change over time?" or "What was the response to this?"
- Explore different angles: "What was the international perspective on this issue?"
""")

st.markdown("""
<div class="tip-box">
<strong>Pro Tip:</strong> The AI Enhancement feature can synthesize information from multiple sources 
to provide comprehensive answers to complex questions. Ask questions like "How did the Daily Worker's 
coverage of strikes evolve between 1930 and 1940?" for rich, contextual responses.
</div>
""", unsafe_allow_html=True)

# Filters and Options
st.markdown("""
<div class="section-header">
    <h2>Search Filters and Options</h2>
</div>
""", unsafe_allow_html=True)

st.markdown("""
### Date Range Filtering
- **Default**: Full coverage (1924-1958) - spans entire Daily Worker archive
- **Custom ranges**: Set specific start and end dates for focused research
- **Historical periods**: Great for studying specific eras like the Great Depression (1929-1939)

### Search Options
- **Maximum Results**: Control how many sources to display (5-50)
- **Relevance Threshold**: Filter out low-relevance results (0.0-1.0)
- **Response Mode**: Choose between Essay Generation or Source Analysis
- **AI Enhancement**: Powered by Gemini AI for intelligent analysis

### Export Options
- **PDF Reports**: Download formatted reports with all results and AI analysis
- **Excel Spreadsheets**: Export source analysis with URLs, dates, and complete AI analysis
- **Conversation History**: Save entire research sessions for later reference
""")

# Understanding Results
st.markdown("""
<div class="section-header">
    <h2>Understanding Your Results</h2>
</div>
""", unsafe_allow_html=True)

st.markdown("""
### Search Results Display
Each search result shows:
- **Source Number**: Sequential numbering (Source 1, Source 2, etc.)
- **Newspaper Name**: Daily Worker, The Worker, or other publications
- **Relevance Score**: Percentage showing how well the content matches your search
- **Citation**: Full citation with publication date and page information
- **Content Excerpt**: Relevant text chunk from the newspaper
- **View on Internet Archive**: Direct link to the original newspaper page

### AI Analysis (When Enabled)
**Essay Generation Mode:**
- Comprehensive synthesis of multiple sources
- Cohesive answer to your research question
- Sources cited as clickable [Source 1], [Source 2] references
- Historical context and interpretation

**Source Analysis Mode:**
- Individual analysis for each source
- Expandable sections for detailed examination
- How each source relates to your specific question
- Perfect for academic research and detailed citation

### Download Options
- **PDF Reports**: Professional formatting with all sources and analysis
- **Excel Export**: Spreadsheet with source details and complete AI analysis
- **Conversation History**: Save your entire research session
""")

st.markdown("""
<div class="tip-box">
<strong>Internet Archive Integration:</strong> All "View on Internet Archive" links open the original newspaper page 
in a new tab. This preserves your search results while letting you examine the full historical context of each source.
</div>
""", unsafe_allow_html=True)

# Example Searches
st.markdown("""
<div class="section-header">
    <h2>Example Searches</h2>
</div>
""", unsafe_allow_html=True)

example_col1, example_col2 = st.columns(2)

with example_col1:
    st.markdown("""
    ### Historical Events & Questions
    - "How did the Daily Worker cover the 1929 Wall Street Crash?"
    - "What was the paper's perspective on the Spanish Civil War?"
    - "How were New Deal programs discussed and analyzed?"
    - "What did the Daily Worker report about Dust Bowl migration?"
    
    ### Labor Movement Questions
    - "How did the Daily Worker cover major steel worker strikes?"
    - "What strategies for union organizing were promoted?"
    - "How were workplace safety issues addressed in the 1930s?"
    - "What was the paper's stance on collective bargaining?"
    """)

with example_col2:
    st.markdown("""
    ### Political & Social Questions
    - "How did the Daily Worker report on Socialist Party activities?"
    - "What was the paper's relationship to the Communist International?"
    - "How did the Daily Worker promote anti-fascist organizing?"
    - "What civil rights issues received coverage in the 1940s?"
    
    ### Social Justice Questions
    - "How did the Daily Worker address housing discrimination?"
    - "What unemployment relief programs were advocated?"
    - "How were women's rights issues covered over time?"
    - "What challenges facing immigrant communities were highlighted?"
    """)

# Troubleshooting
st.markdown("""
<div class="section-header">
    <h2>Troubleshooting</h2>
</div>
""", unsafe_allow_html=True)

st.markdown("""
### Common Issues and Solutions

**No Results Found**
- Try broader search terms or rephrase your question
- Check your date range filters (default covers 1924-1958)
- Lower the relevance threshold setting
- Use more general historical terminology

**Too Many Irrelevant Results**
- Use more specific search terms or focused questions
- Increase the relevance threshold
- Add specific date range filters for focused periods
- Try asking more precise questions about particular events

**AI Analysis Not Working**
- Ensure AI Enhancement is enabled in the sidebar
- Check that you have search results to analyze
- Try refreshing the page if the system seems unresponsive
- Contact support if Gemini AI services appear down

**Export Issues**
- PDF download requires search results with AI analysis
- Excel export only available in Source Analysis mode
- Ensure pop-up blockers aren't preventing downloads
- Check that your browser allows file downloads from the site
""")


# Technical Details
st.markdown("""
<div class="section-header">
    <h2>Technical Details</h2>
</div>
""", unsafe_allow_html=True)

st.markdown("""
### System Information
- **Coverage**: Over 9,900 newspaper issues spanning 34 years (1924-1958)
- **Content**: Daily Worker, The Worker, and related CPUSA publications
- **AI Model**: Gemini for analysis and synthesis
- **Embedding Model**: multilingual-e5-large (Pinecone-hosted)
- **Vector Database**: Pinecone with semantic search capabilities
- **Processing**: 350-word chunks with 75-word overlap for optimal context
- **Data Source**: Internet Archive historical newspapers

### Performance & Features
- **Semantic Search**: Advanced AI embeddings understand natural language questions
- **Parallel Processing**: 25 concurrent operations for faster analysis
- **Real-time Results**: Search results appear immediately while AI processes
- **Export Formats**: PDF reports and Excel spreadsheets with complete analysis
- **Response Modes**: Essay generation and individual source analysis
- **Response Time**: Typically 3-8 seconds depending on complexity and analysis mode

### Recent Enhancements
- **Excel Export**: Complete source analysis in spreadsheet format
- **Improved UI**: Streamlined interface with immediate result display
- **Enhanced Processing**: Faster parallel analysis of multiple sources
- **Better Integration**: Seamless Internet Archive linking and URL reconstruction
""")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #6c757d;">
    <small>
    © 2025 Benjamin Goldstein | AI-powered Daily Worker Search Database<br>
    Software licensed under MIT License | Newspaper content is in the public domain<br>
    Powered by sentence-transformers and Pinecone | Data sourced from Internet Archive
    </small>
</div>
""", unsafe_allow_html=True)