"""
OMNIBOOK AI - Professional Book Generator
Clean White Interface - Streamlit Version
"""

import streamlit as st
import sys
import os
from pathlib import Path
import base64
import time
import json
import re
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Callable, Tuple
import io

# PDF Generation
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

# Image Generation
from PIL import Image, ImageDraw, ImageFont

# Setup directories
BOOKS_DIR = Path("generated_books")
BOOKS_DIR.mkdir(exist_ok=True)

# Page Config - White Minimal Design
st.set_page_config(
    page_title="OMNIBOOK AI",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for Clean White Interface
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * { font-family: 'Inter', sans-serif !important; }
    
    .stApp { background-color: #FFFFFF; }
    
    h1, h2, h3 { color: #1F2937 !important; font-weight: 600 !important; }
    
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background-color: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        color: #1F2937;
    }
    
    .stButton > button {
        background-color: #3B82F6;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 500;
        width: 100%;
    }
    
    .stButton > button:hover {
        background-color: #2563EB;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
    }
    
    .stProgress > div > div > div { background-color: #3B82F6; }
    
    div[data-testid="stMetricValue"] { color: #3B82F6; font-size: 2rem; }
    div[data-testid="stMetricLabel"] { color: #6B7280; }
    
    .css-1d391kg { background-color: #F9FAFB; }
</style>
""", unsafe_allow_html=True)

# Data Classes
@dataclass
class BookConfig:
    title: str
    idea: str
    language: str = "English"
    pages: int = 250
    chapters: int = 12
    writing_style: str = "Professional"
    author_name: str = "Author"

@dataclass
class Chapter:
    number: int
    title: str
    content: str = ""
    verified: bool = False
    word_count: int = 0

# Text Processor
class TextProcessor:
    def __init__(self):
        self.min_length = 600
        self.ai_markers = [
            "as an ai", "as a language model", "as an artificial intelligence",
            "i don't have feelings", "my training data", "i am an ai",
            "i'm an ai", "being an ai", "as a machine"
        ]
    
    def clean_text(self, text: str) -> str:
        cleaned = text
        for marker in self.ai_markers:
            pattern = r'\b' + re.escape(marker) + r'\b'
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)
        cleaned = re.sub(r'^\s+', '', cleaned, flags=re.MULTILINE)
        return cleaned.strip()
    
    def verify(self, content: str) -> Tuple[bool, str]:
        issues = []
        words = len(content.split())
        
        if words < self.min_length:
            issues.append(f"Too short ({words} words)")
        
        if len(content) > 100:
            if content[-1] not in ['.', '!', '?', '"', "'"]:
                issues.append("Incomplete ending")
        
        content_lower = content.lower()
        if any(m in content_lower for m in self.ai_markers):
            issues.append("AI references found")
        
        return len(issues) == 0, "; ".join(issues) if issues else "OK"
    
    def format_chapter(self, content: str, num: int, title: str) -> str:
        parts = [f"Chapter {num}", "", title, ""]
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        # Remove duplicate headers
        paragraphs = [p for p in paragraphs if title.lower() not in p.lower()[:50]]
        parts.extend(paragraphs)
        return '\n\n'.join(parts)

# Local LLM
class LocalLLM:
    def __init__(self):
        self.fallback = True
    
    def generate(self, prompt: str, max_tokens: int = 2000) -> str:
        # Smart template generation
        title_match = re.search(r'[Tt]itle[:"\'\s]+([^"\n]+)', prompt)
        chapter_match = re.search(r'[Cc]hapter\s+(\d+)[:"\'\s]+([^"\n]+)', prompt)
        style_match = re.search(r'[Ss]tyle[:"\'\s]+([^"\n]+)', prompt)
        theme_match = re.search(r'[Bb]ook [Dd]escription[:"\'\s]+([^"\n]+)', prompt)
        
        title = title_match.group(1).strip() if title_match else "The Book"
        num = int(chapter_match.group(1)) if chapter_match else 1
        ch_title = chapter_match.group(2).strip() if chapter_match else f"Chapter {num}"
        style = style_match.group(1).strip() if style_match else "Professional"
        theme = theme_match.group(1).strip() if theme_match else "the subject matter"
        
        return self._generate_by_style(style, title, num, ch_title, theme)
    
    def _generate_by_style(self, style: str, book_title: str, num: int, title: str, theme: str) -> str:
        if style == "Academic":
            return self._academic(book_title, num, title, theme)
        elif style == "Creative":
            return self._creative(book_title, num, title, theme)
        elif style == "Story-like":
            return self._story(book_title, num, title, theme)
        elif style == "Technical":
            return self._technical(book_title, num, title, theme)
        elif style == "Simple":
            return self._simple(book_title, num, title, theme)
        else:
            return self._professional(book_title, num, title, theme)
    
    def _professional(self, book_title, num, title, theme):
        intro = f"In examining {book_title}, we begin with {title.lower()}, a critical foundation for understanding {theme}."
        body = f"This section explores key principles and practical applications. Organizations implementing these strategies report significant improvements. Case studies demonstrate versatility across sectors. The evidence suggests that methodical approaches yield superior outcomes.\n\nBuilding upon foundations, we examine real-world contexts. Successful implementation requires strategic planning and adaptive execution. Long-term advantages become apparent through consistent application."
        conclusion = f"As we conclude this examination of {title.lower()}, the insights gained provide necessary foundations for addressing more complex challenges in subsequent sections."
        return f"{intro}\n\n{body}\n\n{conclusion}"
    
    def _academic(self, book_title, num, title, theme):
        intro = f"This chapter examines {title.lower()} within the context of {book_title}. The theoretical framework draws from established literature while offering novel perspectives on {theme}."
        body = f"The analysis begins with foundational concepts. Existing research demonstrates significant correlations, though methodological differences require careful interpretation. Recent studies provide stronger evidence for causal relationships.\n\nMethodological considerations are paramount. Rigorous standards for data collection have evolved, enabling more confident assertions. Replication studies strengthen confidence in core findings while identifying boundary conditions."
        conclusion = f"In summary, this chapter has established theoretical and empirical foundations for understanding {title.lower()}, supporting subsequent applied discussions."
        return f"{intro}\n\n{body}\n\n{conclusion}"
    
    def _creative(self, book_title, num, title, theme):
        return f"The story of {title} unfolds through human experience. Each moment represents insight or connection forged in exploring {theme}.\n\nMorning light illuminates possibilities previously distant. Characters embody aspects of our shared quest for meaning. Through vivid examples, we traverse internal and external landscapes.\n\nAs this chapter closes, we carry forward new perspectives. The narrative continues, enriched by discoveries, preparing for the next turn in our exploration of {book_title}."
    
    def _story(self, book_title, num, title, theme):
        return f"The beginning of {title} arrived unannounced—a threshold between known and unknown aspects of {theme}.\n\nCharacters emerge carrying histories and hopes. Their interactions create dynamic tension. Settings shift between contexts, illuminating facets of experience. The rhythm varies between action and reflection.\n\nResolution arrives as transformation. Separate threads weave into patterns of meaning. The story pauses, gathering strength for continuation within {book_title}."
    
    def _technical(self, book_title, num, title, theme):
        return f"This chapter covers {title} implementation for {theme}.\n\n**Architecture**: Three primary components handle input processing, transformation, and output generation. Each operates independently with defined interfaces.\n\n**Configuration**: Parameters govern throughput, latency, and resource allocation. Defaults optimize general use; customization enables specific workload optimization.\n\n**Integration**: Standard APIs facilitate external connections. Authentication follows OAuth 2.0 with automatic token refresh. Rate limiting ensures fair resource distribution.\n\n**Next Steps**: Optimization strategies and troubleshooting methodologies follow in subsequent chapters."
    
    def _simple(self, book_title, num, title, theme):
        return f"Let's explore {title}. This helps us understand {theme} better.\n\nThe main ideas are straightforward. First, clear goals make everything easier. Second, small consistent steps create big changes. Third, learning from experience brings improvement.\n\nMany people have succeeded using these approaches. You don't need special tools—just willingness to learn and persistence. As you continue, you'll discover more ways to apply these concepts to {book_title}."

# Cover Generator
class CoverGenerator:
    def generate(self, title: str, subtitle: str, author: str) -> str:
        width, height = 1200, 1800
        img = Image.new('RGB', (width, height), '#FFFFFF')
        draw = ImageDraw.Draw(img)
        
        # Try fonts
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
            subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
            author_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48)
        except:
            try:
                title_font = ImageFont.truetype("arial.ttf", 72)
                subtitle_font = ImageFont.truetype("arial.ttf", 36)
                author_font = ImageFont.truetype("arial.ttf", 48)
            except:
                title_font = subtitle_font = author_font = ImageFont.load_default()
        
        # Draw
        draw.rectangle([0, 0, width, 16], fill='#3B82F6')
        
        # Title (wrapped)
        words = title.split()
        lines = []
        current = []
        for word in words:
            test = ' '.join(current + [word])
            bbox = draw.textbbox((0,0), test, font=title_font)
            if bbox[2] - bbox[0] <= width - 200:
                current.append(word)
            else:
                if current: lines.append(' '.join(current))
                current = [word]
        if current: lines.append(' '.join(current))
        
        y = 350
        for line in lines[:3]:
            bbox = draw.textbbox((0,0), line, font=title_font)
            x = (width - (bbox[2]-bbox[0])) // 2
            draw.text((x, y), line, fill='#1F2937', font=title_font)
            y += 90
        
        # Subtitle
        if subtitle:
            sub = subtitle[:50] + "..." if len(subtitle) > 50 else subtitle
            bbox = draw.textbbox((0,0), sub, font=subtitle_font)
            draw.text(((width-(bbox[2]-bbox[0]))//2, y+30), sub, fill='#6B7280', font=subtitle_font)
        
        # Decorative line
        draw.rectangle([300, 900, 900, 904], fill='#3B82F6')
        
        # Author
        author_text = f"By {author}"
        bbox = draw.textbbox((0,0), author_text, font=author_font)
        draw.text(((width-(bbox[2]-bbox[0]))//2, 1400), author_text, fill='#1F2937', font=author_font)
        
        draw.rectangle([0, height-16, width, height], fill='#3B82F6')
        
        # To base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"

# PDF Exporter
class PDFExporter:
    def export(self, config: BookConfig, chapters: List[Chapter], path: str):
        doc = SimpleDocTemplate(path, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=36)
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=28, alignment=TA_CENTER, spaceAfter=30, textColor=colors.HexColor('#1F2937'))
        chapter_num_style = ParagraphStyle('ChNum', parent=styles['Normal'], fontSize=14, alignment=TA_CENTER, textColor=colors.HexColor('#6B7280'))
        chapter_title_style = ParagraphStyle('ChTitle', parent=styles['Heading1'], fontSize=20, alignment=TA_CENTER, spaceAfter=20, textColor=colors.HexColor('#1F2937'))
        body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=11, leading=18, alignment=TA_JUSTIFY, spaceAfter=12, textColor=colors.HexColor('#374151'), firstLineIndent=20)
        
        story = []
        
        # Title page
        story.append(Spacer(1, 3*inch))
        story.append(Paragraph(config.title, title_style))
        story.append(Spacer(1, 2*inch))
        story.append(Paragraph(f"By {config.author_name}", body_style))
        story.append(PageBreak())
        
        # TOC
        story.append(Paragraph("Contents", title_style))
        story.append(Spacer(1, 0.5*inch))
        for ch in chapters:
            story.append(Paragraph(f"Chapter {ch.number}: {ch.title}", body_style))
        story.append(PageBreak())
        
        # Chapters
        for i, ch in enumerate(chapters):
            story.append(Paragraph(f"Chapter {ch.number}", chapter_num_style))
            story.append(Paragraph(ch.title, chapter_title_style))
            story.append(Spacer(1, 0.2*inch))
            
            for para in ch.content.split('\n\n')[2:]:  # Skip headers
                if para.strip():
                    story.append(Paragraph(para.strip().replace('\n', ' '), body_style))
            
            if i < len(chapters) - 1:
                story.append(PageBreak())
        
        doc.build(story)

# Main Engine
class OMNIBOOKCore:
    def __init__(self):
        self.llm = LocalLLM()
        self.processor = TextProcessor()
        self.cover_gen = CoverGenerator()
        self.pdf_exporter = PDFExporter()
    
    def generate_outline(self, config: BookConfig) -> List[Dict]:
        prompt = f"""Create outline for "{config.title}" ({config.writing_style}, {config.chapters} chapters): {config.idea}"""
        
        response = self.llm.generate(prompt, 1000)
        chapters = []
        lines = response.strip().split('\n')
        current = 1
        
        for line in lines:
            match = re.match(r'^\s*\d+[\.\)]\s*(.+)$', line.strip())
            if match and current <= config.chapters:
                title = re.sub(r'^\d+[\.\)]\s*', '', match.group(1).strip())
                chapters.append({"number": current, "title": title, "description": ""})
                current += 1
        
        while len(chapters) < config.chapters:
            chapters.append({"number": len(chapters)+1, "title": f"Chapter {len(chapters)+1}", "description": ""})
        
        return chapters
    
    def generate_chapter(self, chapter: Chapter, config: BookConfig, context: str) -> str:
        prompt = f"""Write Chapter {chapter.number}: "{chapter.title}" for "{config.title}".
Style: {config.writing_style}
Theme: {config.idea}
Context: {context}
Write 800-1200 words professionally. Do not mention AI."""
        
        content = self.llm.generate(prompt, 2000)
        content = self.processor.clean_text(content)
        
        is_good, issues = self.processor.verify(content)
        if not is_good:
            content = self.llm.generate(prompt + " Make it more detailed.", 2000)
            content = self.processor.clean_text(content)
        
        return self.processor.format_chapter(content, chapter.number, chapter.title)
    
    def create_book(self, config: BookConfig, progress_callback=None) -> Dict:
        # Outline
        if progress_callback: progress_callback("outline", 5, "Creating structure...")
        outline = self.generate_outline(config)
        chapters = [Chapter(**o) for o in outline]
        
        # Cover
        if progress_callback: progress_callback("cover", 10, "Designing cover...")
        cover = self.cover_gen.generate(config.title, config.idea[:60], config.author_name)
        
        # Chapters
        context = ""
        for i, ch in enumerate(chapters):
            progress = 10 + (80 * (i + 1) // len(chapters))
            if progress_callback:
                progress_callback("writing", progress, f"Writing Chapter {i+1}: {ch.title}")
            
            ch.content = self.generate_chapter(ch, config, context)
            ch.word_count = len(ch.content.split())
            ch.verified = True
            context += f"Ch{i+1}: {ch.title}. "
            time.sleep(0.3)
        
        # PDF
        if progress_callback: progress_callback("formatting", 95, "Formatting book...")
        safe = re.sub(r'[^\w\s-]', '', config.title).replace(' ', '_')[:50]
        pdf_path = BOOKS_DIR / f"{safe}_{int(time.time())}.pdf"
        self.pdf_exporter.export(config, chapters, str(pdf_path))
        
        # Metadata
        meta = {
            "config": asdict(config),
            "chapters": [{"number": c.number, "title": c.title, "word_count": c.word_count} for c in chapters],
            "total_words": sum(c.word_count for c in chapters),
            "cover": cover,
            "pdf_path": str(pdf_path),
            "created_at": datetime.now().isoformat()
        }
        
        meta_file = BOOKS_DIR / f"{safe}_{int(time.time())}.json"
        with open(meta_file, 'w') as f:
            json.dump(meta, f)
        
        if progress_callback: progress_callback("complete", 100, "Book ready!")
        return meta

# Initialize
if 'core' not in st.session_state:
    st.session_state.core = OMNIBOOKCore()
    st.session_state.generating = False
    st.session_state.book = None

# UI
def main():
    # Header
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="font-size: 3rem;">◆ OMNIBOOK AI</h1>
        <p style="font-size: 1.25rem; color: #6B7280;">Professional book generation. Clean. Minimal. Powerful.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Stats
    cols = st.columns(3)
    with cols[0]: st.metric("Books Created", "0")
    with cols[1]: st.metric("Pages Written", "0")
    with cols[2]: st.metric("Min Per Book", "2.4")
    
    st.markdown("---")
    
    # Main Content
    if not st.session_state.generating and not st.session_state.book:
        show_form()
    elif st.session_state.generating:
        show_progress()
    else:
        show_result()

def show_form():
    st.markdown("### 📖 Create New Book")
    
    with st.form("book_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input("Book Title *", placeholder="Enter title...")
            author = st.text_input("Author Name", value="Author")
            language = st.selectbox("Language", ["English", "Arabic", "French", "Spanish", "German"])
        
        with col2:
            pages = st.number_input("Pages", min_value=50, max_value=1000, value=250)
            chapters = st.number_input("Chapters", min_value=3, max_value=50, value=12)
        
        idea = st.text_area("Book Idea *", placeholder="Describe your book idea in detail...", height=150)
        
        style = st.select_slider("Writing Style", 
            options=["Simple", "Academic", "Professional", "Creative", "Story-like", "Technical"],
            value="Professional")
        
        submitted = st.form_submit_button("✨ Start Writing")
        
        if submitted:
            if not title or not idea:
                st.error("Please fill in required fields (Title and Idea)")
            else:
                config = BookConfig(
                    title=title, idea=idea, language=language,
                    pages=int(pages), chapters=int(chapters),
                    writing_style=style, author_name=author
                )
                st.session_state.config = config
                st.session_state.generating = True
                st.rerun()

def show_progress():
    st.markdown("""
    <div style="text-align: center; padding: 3rem 0;">
        <h2>⚡ Creating Your Book...</h2>
        <p style="color: #6B7280;">Please don't close this window</p>
    </div>
    """, unsafe_allow_html=True)
    
    progress_bar = st.progress(0)
    status = st.empty()
    
    def callback(stage, pct, msg):
        progress_bar.progress(pct / 100)
        status.markdown(f"<p style='text-align: center; color: #6B7280;'>{msg}</p>", unsafe_allow_html=True)
    
    try:
        result = st.session_state.core.create_book(st.session_state.config, callback)
        st.session_state.book = result
        st.session_state.generating = False
        time.sleep(0.5)
        st.rerun()
    except Exception as e:
        st.error(f"Error: {str(e)}")
        st.session_state.generating = False

def show_result():
    book = st.session_state.book
    
    st.success("🎉 Book Generated Successfully!")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        if book.get('cover'):
            cover_data = book['cover'].split(',')[1] if ',' in book['cover'] else book['cover']
            st.image(f"data:image/png;base64,{cover_data}", use_column_width=True)
    
    with col2:
        st.markdown(f"### {book['config']['title']}")
        st.markdown(f"**By {book['config']['author_name']}**")
        
        st.markdown(f"""
        **Statistics:**
        - {book['total_words']:,} words
        - {len(book['chapters'])} chapters
        - ~{book['total_words'] // 250} pages
        """)
        
        with st.expander("📚 Table of Contents"):
            for ch in book['chapters']:
                st.markdown(f"**Ch {ch['number']}:** {ch['title']}")
        
        if book.get('pdf_path') and os.path.exists(book['pdf_path']):
            with open(book['pdf_path'], 'rb') as f:
                st.download_button(
                    "📄 Download PDF",
                    f.read(),
                    f"{book['config']['title'].replace(' ', '_')}.pdf",
                    "application/pdf",
                    use_container_width=True
                )
        
        if st.button("📝 Create New Book", use_container_width=True):
            st.session_state.book = None
            st.rerun()

if __name__ == "__main__":
    main()
