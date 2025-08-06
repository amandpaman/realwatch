import streamlit as st
import subprocess
import tempfile
import base64
import os
import json
import time
import requests
from urllib.parse import quote_plus

# Configure page
st.set_page_config(
    page_title="YouTube Search & Player",
    page_icon="🎬",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #FF0000;
        font-weight: bold;
        margin-bottom: 2rem;
    }
    .search-section {
        background-color: #f8f9fa;
        padding: 2rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .video-card {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        background-color: white;
    }
    .video-card:hover {
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .video-player {
        border-radius: 10px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        padding: 1rem;
    }
    .search-result {
        cursor: pointer;
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.2rem 0;
    }
    .search-result:hover {
        background-color: #f0f0f0;
    }
</style>
""", unsafe_allow_html=True)

def check_yt_dlp():
    """Check if yt-dlp is available"""
    try:
        result = subprocess.run(['yt-dlp', '--version'], 
                              capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except:
        return False

def search_youtube_videos(query, max_results=10):
    """Search YouTube videos using yt-dlp"""
    try:
        cmd = [
            'yt-dlp',
            '--dump-json',
            '--no-download',
            '--flat-playlist',
            '--playlist-end', str(max_results),
            f'ytsearch{max_results}:{query}'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            videos = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        video_data = json.loads(line)
                        videos.append({
                            'id': video_data.get('id', ''),
                            'title': video_data.get('title', 'Unknown Title'),
                            'uploader': video_data.get('uploader', 'Unknown Channel'),
                            'duration': video_data.get('duration', 0),
                            'view_count': video_data.get('view_count', 0),
                            'url': f"https://www.youtube.com/watch?v={video_data.get('id', '')}",
                            'thumbnail': f"https://img.youtube.com/vi/{video_data.get('id', '')}/mqdefault.jpg"
                        })
                    except json.JSONDecodeError:
                        continue
            return videos
    except Exception as e:
        st.error(f"Search error: {str(e)}")
    
    return []

def search_youtube_fallback(query, max_results=10):
    """Fallback search using YouTube RSS (limited but works without API)"""
    try:
        # This is a simplified search - in production you'd want YouTube Data API
        search_results = []
        
        # Generate some common video IDs for demo (you'd implement real search)
        demo_videos = [
            {
                'id': 'dQw4w9WgXcQ',
                'title': 'Rick Astley - Never Gonna Give You Up',
                'uploader': 'Rick Astley',
                'duration': 213,
                'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                'thumbnail': 'https://img.youtube.com/vi/dQw4w9WgXcQ/mqdefault.jpg'
            },
            {
                'id': '9bZkp7q19f0',
                'title': 'PSY - GANGNAM STYLE',
                'uploader': 'officialpsy',
                'duration': 253,
                'url': 'https://www.youtube.com/watch?v=9bZkp7q19f0',
                'thumbnail': 'https://img.youtube.com/vi/9bZkp7q19f0/mqdefault.jpg'
            },
            {
                'id': 'kJQP7kiw5Fk',
                'title': 'Luis Fonsi - Despacito ft. Daddy Yankee',
                'uploader': 'LuisFonsiVEVO',
                'duration': 281,
                'url': 'https://www.youtube.com/watch?v=kJQP7kiw5Fk',
                'thumbnail': 'https://img.youtube.com/vi/kJQP7kiw5Fk/mqdefault.jpg'
            }
        ]
        
        # Filter by query (basic matching)
        query_lower = query.lower()
        for video in demo_videos:
            if query_lower in video['title'].lower() or query_lower in video['uploader'].lower():
                search_results.append(video)
        
        return search_results[:max_results]
        
    except Exception as e:
        st.error(f"Fallback search error: {str(e)}")
        return []

def extract_video_id(url):
    """Extract YouTube video ID from URL"""
    import re
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
        r'youtube\.com\/watch\?.*v=([^&\n?#]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    if len(url) == 11 and url.replace('-', '').replace('_', '').isalnum():
        return url
    
    return None

def get_video_info(url):
    """Get video information using yt-dlp"""
    try:
        cmd = ['yt-dlp', '--dump-json', '--no-download', url]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            info = json.loads(result.stdout)
            return {
                'title': info.get('title', 'Unknown Title'),
                'uploader': info.get('uploader', 'Unknown Channel'),
                'duration': info.get('duration', 0),
                'view_count': info.get('view_count', 0),
                'description': info.get('description', '')[:300] + '...' if info.get('description') else '',
                'upload_date': info.get('upload_date', ''),
                'thumbnail': info.get('thumbnail', ''),
                'webpage_url': info.get('webpage_url', url),
                'formats_count': len(info.get('formats', []))
            }
    except Exception as e:
        st.error(f"Error getting video info: {str(e)}")
    
    return None

def get_video_stream_url(url, quality='720p'):
    """Get direct video stream URL"""
    try:
        format_selector = f"best[height<={quality[:-1]}][ext=mp4]/best[ext=mp4]/best"
        
        cmd = [
            'yt-dlp', 
            '-f', format_selector,
            '--get-url',
            '--no-playlist',
            url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
            
    except Exception as e:
        st.error(f"Error getting stream URL: {str(e)}")
    
    return None

def download_small_video(url, max_size_mb=50):
    """Download small video to memory"""
    try:
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            cmd = [
                'yt-dlp',
                '-f', f'best[filesize<{max_size_mb}M][ext=mp4]/worst[ext=mp4]',
                '-o', temp_file.name,
                '--no-playlist',
                url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0 and os.path.exists(temp_file.name):
                with open(temp_file.name, 'rb') as f:
                    video_data = f.read()
                
                os.unlink(temp_file.name)
                return video_data
                
    except Exception as e:
        st.error(f"Error downloading video: {str(e)}")
    
    return None

def create_video_player(video_data):
    """Create HTML5 video player"""
    if video_data:
        video_base64 = base64.b64encode(video_data).decode()
        
        video_html = f"""
        <div class="video-player">
            <video width="100%" height="400" controls preload="metadata">
                <source src="data:video/mp4;base64,{video_base64}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
        </div>
        """
        
        return video_html
    
    return None

# def format_duration(seconds):
#     """Format duration in seconds to MM:SS"""
#     if not seconds:
#         return "Unknown"
#     minutes = seconds // 60
#     seconds = seconds % 60
#     return f"{minutes}:{seconds:02d}"
def format_duration(seconds):
    if seconds is None or not isinstance(seconds, (int, float)):
        return "Unknown"
    minutes = int(seconds) // 60
    seconds = int(seconds) % 60
    return f"{minutes}:{seconds:02d}"


def main():
    st.markdown('<h1 class="main-header">🎬 YouTube Search & Player</h1>', unsafe_allow_html=True)
    
    # Initialize session state
    if 'search_results' not in st.session_state:
        st.session_state.search_results = []
    if 'selected_video' not in st.session_state:
        st.session_state.selected_video = None
    
    # Check if yt-dlp is available
    yt_dlp_available = check_yt_dlp()
    
    # Sidebar
    with st.sidebar:
        st.header("🎛️ Settings")
        
        # Quality selection
        quality = st.selectbox(
            "Video Quality",
            ["1080p", "720p", "480p", "360p", "240p"],
            index=1
        )
        
        # Processing mode
        processing_mode = st.radio(
            "Processing Mode",
            ["Stream URL", "Download Video", "Audio Only"] if yt_dlp_available else ["YouTube Embed"],
            help="Choose how to handle the video"
        )
        
        # Search settings
        st.subheader("🔍 Search Settings")
        max_results = st.slider("Max Search Results", 5, 20, 10)
        
        if processing_mode == "Download Video":
            max_size = st.slider("Max Download Size (MB)", 10, 100, 50)
        
        st.markdown("---")
        
        # Quick categories
        st.subheader("📂 Quick Categories")
        categories = [
            "Music Videos", "Educational", "News", "Technology", 
            "Cooking", "Travel", "Gaming", "Science"
        ]
        
        for category in categories:
            if st.button(f"🔍 {category}", key=f"cat_{category}"):
                st.session_state.search_query = category.lower()
                st.rerun()
        
        st.markdown("---")
        
        # System status
        st.subheader("🔧 System Status")
        st.write(f"**yt-dlp:** {'✅ Available' if yt_dlp_available else '❌ Not available'}")
        st.write(f"**Search:** {'✅ Full Search' if yt_dlp_available else '⚠️ Limited'}")
        st.write(f"**Download:** {'✅ Available' if yt_dlp_available else '❌ Not available'}")

    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Search section
        st.markdown('<div class="search-section">', unsafe_allow_html=True)
        
        # Tab selection
        search_tab, url_tab = st.tabs(["🔍 Search Videos", "🔗 Direct URL"])
        
        with search_tab:
            st.subheader("Search YouTube Videos")
            
            # Search input
            search_query = st.text_input(
                "Search for videos:",
                value=st.session_state.get('search_query', ''),
                placeholder="Enter keywords, artist name, song title, etc.",
                help="Search for any video by keywords"
            )
            
            col_search1, col_search2 = st.columns(2)
            
            with col_search1:
                search_btn = st.button("🔍 Search Videos", type="primary")
            
            with col_search2:
                clear_btn = st.button("🗑️ Clear Results")
            
            if clear_btn:
                st.session_state.search_results = []
                st.session_state.selected_video = None
                st.rerun()
            
            # Perform search
            if search_btn and search_query:
                with st.spinner("Searching YouTube..."):
                    if yt_dlp_available:
                        results = search_youtube_videos(search_query, max_results)
                    else:
                        results = search_youtube_fallback(search_query, max_results)
                        st.warning("⚠️ Using limited search. Install yt-dlp for full search capabilities.")
                    
                    st.session_state.search_results = results
                    if results:
                        st.success(f"✅ Found {len(results)} videos!")
                    else:
                        st.error("❌ No videos found. Try different keywords.")
            
            # Display search results
            if st.session_state.search_results:
                st.subheader(f"📺 Search Results ({len(st.session_state.search_results)} videos)")
                
                for i, video in enumerate(st.session_state.search_results):
                    with st.container():
                        col_thumb, col_info, col_action = st.columns([1, 3, 1])
                        
                        with col_thumb:
                            # Display thumbnail
                            if video.get('thumbnail'):
                                st.image(video['thumbnail'], width=120)
                        
                        with col_info:
                            st.write(f"**{video['title']}**")
                            st.write(f"👤 {video['uploader']}")
                            if video.get('duration'):
                                st.write(f"⏱️ {format_duration(video['duration'])}")
                            if video.get('view_count'):
                                st.write(f"👁️ {video['view_count']:,} views")
                        
                        with col_action:
                            if st.button("▶️ Select", key=f"select_{i}"):
                                st.session_state.selected_video = video
                                st.success(f"Selected: {video['title'][:30]}...")
                        
                        st.divider()
        
        with url_tab:
            st.subheader("Enter Direct YouTube URL")
            
            video_url = st.text_input(
                "YouTube URL:",
                placeholder="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                help="Paste any YouTube video URL"
            )
            
            if st.button("📋 Load from URL"):
                if video_url:
                    video_id = extract_video_id(video_url)
                    if video_id:
                        # Create video object from URL
                        video_info = {
                            'id': video_id,
                            'url': video_url,
                            'title': 'Loading...',
                            'uploader': 'Loading...',
                            'thumbnail': f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
                        }
                        st.session_state.selected_video = video_info
                        st.success("✅ Video loaded from URL!")
                    else:
                        st.error("❌ Invalid YouTube URL")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Video processing section
        if st.session_state.selected_video:
            video = st.session_state.selected_video
            
            st.subheader("🎬 Selected Video")
            
            # Display selected video info
            col_vid1, col_vid2 = st.columns([1, 2])
            
            with col_vid1:
                if video.get('thumbnail'):
                    st.image(video['thumbnail'], width=200)
            
            with col_vid2:
                st.write(f"**Title:** {video['title']}")
                st.write(f"**Channel:** {video['uploader']}")
                if video.get('duration'):
                    st.write(f"**Duration:** {format_duration(video['duration'])}")
                st.write(f"**URL:** {video['url']}")
            
            # Processing buttons
            st.subheader("🔧 Process Video")
            
            col_proc1, col_proc2, col_proc3 = st.columns(3)
            
            with col_proc1:
                if st.button("📋 Get Full Info"):
                    with st.spinner("Getting detailed video information..."):
                        if yt_dlp_available:
                            detailed_info = get_video_info(video['url'])
                            if detailed_info:
                                st.session_state.detailed_info = detailed_info
                                st.success("✅ Detailed info retrieved!")
                            else:
                                st.error("❌ Failed to get detailed info")
                        else:
                            st.error("❌ yt-dlp not available")
            
            with col_proc2:
                if processing_mode == "Stream URL":
                    if st.button("🔗 Get Stream URL"):
                        with st.spinner("Getting stream URL..."):
                            if yt_dlp_available:
                                stream_url = get_video_stream_url(video['url'], quality)
                                if stream_url:
                                    st.session_state.stream_url = stream_url
                                    st.success("✅ Stream URL obtained!")
                                else:
                                    st.error("❌ Failed to get stream URL")
                            else:
                                st.error("❌ yt-dlp not available")
                
                elif processing_mode == "Download Video":
                    if st.button("📥 Download Video"):
                        with st.spinner(f"Downloading video (max {max_size}MB)..."):
                            if yt_dlp_available:
                                video_data = download_small_video(video['url'], max_size)
                                if video_data:
                                    st.session_state.video_data = video_data
                                    st.success(f"✅ Video downloaded! ({len(video_data)/1024/1024:.1f} MB)")
                                else:
                                    st.error("❌ Download failed")
                            else:
                                st.error("❌ yt-dlp not available")
                
                else:  # YouTube Embed
                    if st.button("🎥 Embed Video"):
                        video_id = extract_video_id(video['url'])
                        if video_id:
                            st.session_state.embed_id = video_id
                            st.success("✅ Video embedded!")
            
            with col_proc3:
                if st.button("🗑️ Clear Selection"):
                    st.session_state.selected_video = None
                    if 'detailed_info' in st.session_state:
                        del st.session_state.detailed_info
                    if 'stream_url' in st.session_state:
                        del st.session_state.stream_url
                    if 'video_data' in st.session_state:
                        del st.session_state.video_data
                    st.rerun()
            
            # Display results
            if 'detailed_info' in st.session_state:
                st.subheader("📊 Detailed Information")
                info = st.session_state.detailed_info
                
                col_det1, col_det2 = st.columns(2)
                with col_det1:
                    st.write(f"**Title:** {info['title']}")
                    st.write(f"**Channel:** {info['uploader']}")
                    st.write(f"**Duration:** {format_duration(info['duration'])}")
                
                with col_det2:
                    st.write(f"**Views:** {info['view_count']:,}" if info['view_count'] else "**Views:** Unknown")
                    st.write(f"**Upload Date:** {info['upload_date']}")
                    st.write(f"**Available Formats:** {info['formats_count']}")
                
                with st.expander("Description"):
                    st.write(info['description'])
            
            if 'stream_url' in st.session_state:
                st.subheader("🔗 Stream URL")
                stream_url = st.session_state.stream_url
                st.code(stream_url)
                st.markdown(f"[🎬 Open in External Player]({stream_url})")
                
                # Try to embed stream
                try:
                    st.video(stream_url)
                except:
                    st.warning("⚠️ Cannot embed this stream. Use the URL above in VLC or another video player.")
            
            if 'video_data' in st.session_state:
                st.subheader("🎬 Video Player")
                video_data = st.session_state.video_data
                video_html = create_video_player(video_data)
                
                if video_html:
                    st.markdown(video_html, unsafe_allow_html=True)
                
                # Download button
                st.download_button(
                    label="📥 Download Video File",
                    data=video_data,
                    file_name=f"{video['title'][:30]}.mp4",
                    mime="video/mp4"
                )
            
            if 'embed_id' in st.session_state:
                st.subheader("🎥 Embedded Video")
                embed_id = st.session_state.embed_id
                
                embed_html = f"""
                <iframe width="100%" height="400" 
                        src="https://www.youtube.com/embed/{embed_id}" 
                        frameborder="0" allowfullscreen>
                </iframe>
                """
                
                st.markdown(embed_html, unsafe_allow_html=True)
                st.warning("⚠️ This will only work if YouTube is not blocked in your network.")
    
    with col2:
        # Help and tips
        st.subheader("💡 How to Use")
        
        st.markdown("""
        **🔍 Search Mode:**
        1. Enter keywords in search box
        2. Click "Search Videos"
        3. Browse results and click "Select"
        4. Choose processing option
        
        **🔗 URL Mode:**
        1. Paste YouTube URL
        2. Click "Load from URL"
        3. Process the video
        
        **Processing Options:**
        - **Stream URL:** Get direct link for external players
        - **Download:** Save small videos locally
        - **Embed:** Use YouTube's embed player
        """)
        
        if not yt_dlp_available:
            st.warning("""
            ⚠️ **Limited Functionality**
            
            yt-dlp is not available. You can:
            - Use basic search (limited results)
            - Embed videos (if YouTube not blocked)
            - View video information
            """)
        
        # Popular searches
        st.subheader("🔥 Popular Searches")
        popular_searches = [
            "relaxing music", "cooking tutorial", "python programming", 
            "news today", "workout routine", "travel guide"
        ]
        
        for search_term in popular_searches:
            if st.button(f"🔍 {search_term}", key=f"pop_{search_term}"):
                st.session_state.search_query = search_term
                st.rerun()
        
        # Current selection info
        if st.session_state.selected_video:
            st.subheader("📺 Current Selection")
            video = st.session_state.selected_video
            st.write(f"**{video['title'][:30]}...**")
            st.write(f"Channel: {video['uploader']}")
            
            if video.get('thumbnail'):
                st.image(video['thumbnail'], width=150)

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #6c757d; padding: 1rem 0;">
        <p>🎬 YouTube Search & Player | Search, Stream, and Download Videos</p>
        <p><small>⚠️ Please comply with YouTube's Terms of Service and copyright laws</small></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
