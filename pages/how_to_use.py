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
    # Read and encode the image
    with open(masthead_path, "rb") as img_file:
        img_base64 = base64.b64encode(img_file.read()).decode()
    
    st.markdown(f"""
    <div class="main-header">
        <div style="display: flex; align-items: center; justify-content: center; gap: 2rem; flex-wrap: wrap;">
            <div style="flex: 1; text-align: center; min-width: 300px;">
                <h1>How to Use the AI-powered Daily Worker Search</h1>
                <p>Complete guide to searching the CPUSA's Daily Worker archive</p>
            </div>
            <div style="flex: 0 0 auto;">
                <img src="data:image/jpeg;base64,{img_base64}" 
                     alt="Daily Worker Masthead from January 1, 1935" 
                     style="max-height: 120px; width: auto; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.2); 
                            object-fit: contain; object-position: top;">
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    # Fallback if image not found
    st.markdown("""
    <div class="main-header">
        <div style="text-align: center;">
            <h1>How to Use the AI-powered Daily Worker Search</h1>
            <p>Complete guide to searching the CPUSA's Daily Worker archive</p>
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
history, social movements, and political developments. Use this guide to make the most of your searches.
""")

# Search Methods
st.markdown("""
<div class="section-header">
    <h2>Search Methods</h2>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Hybrid Search (Recommended)")
    st.markdown("""
    **Best for comprehensive searches**
    - Combines semantic understanding with keyword matching
    - Finds related concepts even if exact words aren't used
    - Ask full questions: "How did workers respond to the Great Depression?"
    - Example: "What was the Daily Worker's position on the Spanish Civil War?"
    """)

with col2:
    st.subheader("Semantic Search")
    st.markdown("""
    **Best for natural language questions**
    - Understands meaning and context
    - Ask complete questions in natural language
    - Example: "How did unemployment affect working families during the 1930s?"
    - Try: "What were the main criticisms of Roosevelt's New Deal policies?"
    """)

with col3:
    st.subheader("Keyword Search")
    st.markdown("""
    **Best for exact terms**
    - Traditional keyword matching
    - Finds exact words and phrases
    - Example: Search "John Smith" to find that specific name
    """)

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

# Filters and Advanced Options
st.markdown("""
<div class="section-header">
    <h2>Filters and Advanced Options</h2>
</div>
""", unsafe_allow_html=True)

st.markdown("""
### Date Range Filtering
- **Default**: Last 100 years from today
- **Custom ranges**: Set specific start and end dates
- **Historical context**: Remember publication dates span from early 1900s onward

### Advanced Settings
- **Maximum Results**: Control how many results to display (5-50)
- **Relevance Threshold**: Filter out low-relevance results (0.0-1.0)
- **AI Enhancement**: Generate comprehensive summaries using Gemini AI
""")

# Understanding Results
st.markdown("""
<div class="section-header">
    <h2>Understanding Your Results</h2>
</div>
""", unsafe_allow_html=True)

st.markdown("""
### Result Information
Each search result shows:
- **Source Number**: Sequential numbering of results
- **Newspaper Name**: Daily Worker, The Worker, etc.
- **Relevance Score**: Percentage showing how well the content matches your search
- **Citation**: Publication date and page information
- **View Source Link**: Direct link to the Internet Archive page

### AI Summary
When enabled, the AI Enhancement provides:
- Synthesized information from top search results
- Comprehensive answers to your questions
- Historical context and analysis
""")

st.markdown("""
<div class="tip-box">
<strong>Internet Archive Links:</strong> Click "View Source" to see the original newspaper page 
on the Internet Archive website. This opens in a new tab so you don't lose your search results.
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
- Try broader search terms
- Check your date range filters
- Lower the relevance threshold
- Switch to a different search method

**Too Many Irrelevant Results**
- Use more specific search terms
- Increase the relevance threshold
- Add date range filters
- Try keyword search for exact phrases

**AI Summary Not Available**
- Ensure GEMINI_API_KEY is configured
- Check that AI Enhancement is enabled in Advanced Options
- Verify you have search results to summarize
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
- **Content**: Daily Worker and The Worker publications
- **Embedding Model**: multilingual-e5-large (Pinecone-hosted)
- **Vector Database**: Pinecone with hybrid BM25 search
- **Processing**: 350-word chunks with 75-word overlap
- **Data Source**: Internet Archive historical newspapers

### Search Performance
- **Semantic Search**: Advanced AI embeddings for natural language questions
- **Keyword Search**: BM25 algorithm for exact term matching  
- **Hybrid Search**: Combines both methods with intelligent scoring
- **AI Enhancement**: Gemini-powered synthesis for comprehensive answers
- **Response Time**: Typically 2-5 seconds depending on query complexity
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